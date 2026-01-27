import sys
import typing

# Python 3.9 Compatibility Patch
if sys.version_info < (3, 10):
    try:
        from typing_extensions import TypeAlias
        typing.TypeAlias = TypeAlias
    except ImportError:
        pass

import asyncio
import json
import logging
import time
from livekit import rtc
from typing import Dict, List, Optional, Any
from enum import Enum

from app.domain.services.conductor_writer import ConductorWriter
from app.metrics.engine import MetricsEngine
from app.domain.services.transcript_resolver import TranscriptResolver
from app.livekit.protocol import AgentPacket, MsgType, SpeakCmdPayload
from app.livekit.protocol import AgentPacket, MsgType, SpeakCmdPayload, PlayAssetCmdPayload
from app.domain.services.llm_service import LLMService
from app.livekit.speculative import SpecPlanner, SpecPlan

import io
import wave
# from app.domain.services.stt_service import STTService

logger = logging.getLogger(__name__)

class ConductorState(str, Enum):
    INIT = "INIT"
    PLAYING_SEED = "PLAYING_SEED"
    LIVE = "LIVE"
    PAUSED = "PAUSED"
    REPLAYING = "REPLAYING"
    ENDING = "ENDING"

from app.domain.services.rewind_service import RewindService

from app.db.repos.replay_event_repo import ReplayEventRepo
from app.livekit.session_clock import SessionClock

class Conductor:
    def __init__(self, writer: ConductorWriter, metrics_engine: MetricsEngine, resolver: TranscriptResolver, rewind_service: RewindService, replay_event_repo: ReplayEventRepo):
        self.writer = writer
        self.metrics_engine = metrics_engine
        self.resolver = resolver
        self.rewind_service = rewind_service
        self.replay_event_repo = replay_event_repo
        self.room = rtc.Room()
        
        # Session Clock (Timekeeping Epic)
        self.clock = SessionClock()
        
        self.state = ConductorState.INIT
        self.session_id: Optional[str] = None
        self.branch_id: Optional[str] = None
        
        self.current_speaker: Optional[str] = None
        self.current_turn_id: Optional[str] = None
        self.seed_task = None
        
        # Runtime State (Ticket 2)
        self.history_cache: List[str] = []
        self.state_version: int = 0
        
        # Speculative Planning (Ticket 3/4)
        self.spec_planner: Optional[SpecPlanner] = None
        self.spec_plan: Optional[SpecPlan] = None
        self.spec_plan_task: Optional[asyncio.Task] = None
        
        # Synchronization
        self.live_loop_signal = asyncio.Event()
        self.playback_done_event = asyncio.Event()

        # Telemetry
        # Telemetry
        self.live_loop_signal: Optional[asyncio.Event] = None
        self.t_playback_done: float = 0.0
        
        # PTT / STT State
        self.is_recording_facilitator = False
        self.is_processing_intervention = False
        self.intervention_stats = {}
        # Audio handling removed (Worker)
        
        # Event handlers
        
        # Event handlers
        self.room.on("data_received", self.on_data_received)
        self.room.on("participant_disconnected", self.on_participant_disconnected)
        self.room.on("track_subscribed", self.on_track_subscribed)

    async def connect(self, url: str, token: str, session_id: str, branch_id: str):
        self.session_id = session_id
        self.branch_id = branch_id
        await self.room.connect(url, token)
        logger.info(f"Conductor connected to room {self.room.name}")
        
        # Start session clock
        self.clock.start()
        
        # Broadcast initial clock sync to frontend
        await self.broadcast_clock_sync()
        
        # Initial transition
        await self.transition_to(ConductorState.PLAYING_SEED)

    async def disconnect(self):
        await self.transition_to(ConductorState.ENDING)
        await self.room.disconnect()

    async def transition_to(self, new_state: ConductorState):
        logger.info(f"State transition: {self.state} -> {new_state} [Session: {self.session_id}]")
        self.state = new_state
        
        if new_state == ConductorState.PLAYING_SEED:
            self.seed_task = asyncio.create_task(self._run_seed_playback())
        elif new_state == ConductorState.LIVE:
            self.seed_task = asyncio.create_task(self._run_live_loop())
        elif new_state == ConductorState.PAUSED:
            if self.seed_task: self.seed_task.cancel()
            if self.spec_plan_task: self.spec_plan_task.cancel()
            # Stop audio?
            if self.current_speaker:
                asyncio.create_task(self.send_stop_cmd(self.current_speaker))
                
        elif new_state == ConductorState.REPLAYING:
            self.seed_task = asyncio.create_task(self._run_replay_loop())
            
        elif new_state == ConductorState.ENDING:
            if self.seed_task:
                self.seed_task.cancel()
            if self.spec_plan_task:
                self.spec_plan_task.cancel()
            # Cleanup STT (Removed)

    # -------------------------------------------------------------------------
    # Message Handling (Task 0.2)
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Message Handling (Task 0.2)
    # -------------------------------------------------------------------------
    def on_data_received(self, event):
        try:
            # Extract fields from event object
            data = event.data
            participant = event.participant
            kind = event.kind

            # Decode using protocol
            payload_str = data.decode("utf-8")
            raw_msg = json.loads(payload_str)
            
            # Validation
            try:
                packet = AgentPacket(**raw_msg)
            except Exception as e:
                logger.warning(f"Invalid message format from {participant.identity}: {e}")
                return

            self._handle_packet(packet, participant.identity)

        except Exception as e:
            logger.error(f"Error handling data: {e}")

    def _handle_packet(self, packet: AgentPacket, sender_id: str):
        logger.info(f"Received {packet.type} from {sender_id}: {packet.payload}")
        
        if packet.type == MsgType.FAC_START:
            # Start PTT
            self.is_recording_facilitator = True
            self.is_processing_intervention = True
            
            # Record facilitator timing (Ticket 3)
            t_start_ms = int(self.clock.now_ms())
            wall_start_ts = time.time()
            self._pending_facilitator_timing = {
                "t_start_ms": t_start_ms,
                "wall_start_ts": wall_start_ts,
                "sender_id": sender_id
            }
            logger.info(f"Facilitator PTT start at t={t_start_ms}ms")
            
            try:
                # Removed: self.audio_capture_buffer.clear() - Worker handles audio
                pass
            except Exception: pass
            
            asyncio.create_task(self._process_intervention(sender_id))
            
            # Cancel Speculation (Ticket 5)
            if self.spec_plan_task:
                self.spec_plan_task.cancel()
            self.spec_plan = None
            self.state_version += 1
            
            # Send ACK (Reliability Task 3.1)
            asyncio.create_task(self._send_fac_ack(sender_id))
            
        elif packet.type == MsgType.FAC_END:
            # Stop PTT & Finalize
            logger.info(f"Facilitator {sender_id} released PTT.")
            self.is_recording_facilitator = False
            
            # Record facilitator timing (Ticket 3)
            if hasattr(self, '_pending_facilitator_timing') and self._pending_facilitator_timing:
                t_end_ms = int(self.clock.now_ms())
                wall_end_ts = time.time()
                self._pending_facilitator_timing["t_end_ms"] = t_end_ms
                self._pending_facilitator_timing["wall_end_ts"] = wall_end_ts
                logger.info(f"Facilitator PTT end at t={t_end_ms}ms (duration: {t_end_ms - self._pending_facilitator_timing['t_start_ms']}ms)")
            
            # Wait for TRANSCRIPT_COMPLETE
            
        elif packet.type == MsgType.TRANSCRIPT_COMPLETE:
            self._handle_transcript_complete(packet.payload)
            
        elif packet.type == MsgType.PLAYBACK_DONE:
            # Validate turn_id
            if packet.turn_id and packet.turn_id != self.current_turn_id:
                logger.warning(f"Received stale/mismatched PLAYBACK_DONE: {packet.turn_id} != {self.current_turn_id}")
                return

            self.playback_done_event.set()
            # Telemetry: Log gap start
            self.t_playback_done = time.time()
            
            # Record t_end_ms (Ticket 2)
            t_end_ms = int(self.clock.now_ms())
            wall_end_ts = time.time()
            
            # Finalize pending timing and store
            if hasattr(self, '_pending_turn_timing') and packet.turn_id in self._pending_turn_timing:
                timing_data = self._pending_turn_timing.pop(packet.turn_id)
                timing_data["t_end_ms"] = t_end_ms
                timing_data["wall_end_ts"] = wall_end_ts
                
                # Store for later use when committing utterance
                if not hasattr(self, '_completed_turn_timing'):
                    self._completed_turn_timing = {}
                self._completed_turn_timing[packet.turn_id] = timing_data
                
                logger.info(f"Turn {packet.turn_id} timing: {timing_data['t_start_ms']}ms - {t_end_ms}ms")
            
            # Store playback metadata for commit
            self.last_playback_duration = packet.payload.get("duration_ms", 0)
            self.last_playback_audio_url = packet.payload.get("audio_url")
            
            # Relay to frontend for UI update
            asyncio.create_task(self.broadcast_playback_done(sender_id))
            if self.live_loop_signal:
                self.live_loop_signal.set()
        elif packet.type == MsgType.FINISH:
            logger.info("Received FINISH command from facilitator.")
            asyncio.create_task(self.transition_to(ConductorState.ENDING))
            
        elif packet.type == MsgType.TIME_STOP:
            logger.info("Received TIME_STOP command.")
            # Pause clock (Ticket 5)
            paused_at = self.clock.pause()
            asyncio.create_task(self.broadcast_clock_pause(paused_at))
            asyncio.create_task(self.transition_to(ConductorState.PAUSED))
            
        elif packet.type == MsgType.REWIND_TO:
            logger.info(f"Received REWIND_TO: {packet.payload}")
            asyncio.create_task(self._handle_rewind_to(packet.payload))
            
        elif packet.type == MsgType.REWIND_CANCEL:
            logger.info("Received REWIND_CANCEL.")
            # Resume clock (Ticket 5)
            resumed_at = self.clock.resume()
            asyncio.create_task(self.broadcast_clock_resume(resumed_at))
            asyncio.create_task(self.transition_to(ConductorState.LIVE))

    async def _process_intervention(self, sender_id: str):
        self.intervention_stats = {'t_fac_start': time.time(), 'sender': sender_id}
        logger.info(f"Facilitator intervention started by {sender_id}")
        
        if self.state == ConductorState.PLAYING_SEED:
            if self.seed_task:
                self.seed_task.cancel()
            await self.transition_to(ConductorState.LIVE)
        
        # Invalidate speculation (Ticket 5)
        self.state_version += 1
        
        # Stop current speaker
        if self.current_speaker:
            await self.send_stop_cmd(self.current_speaker)
            # If we are in LIVE loop, we need to interrupt the wait?
            if self.live_loop_signal:
                self.live_loop_signal.set() # Force loop to wake up and re-evaluate
        
        self.intervention_stats['t_audio_stopped'] = time.time()

    # -------------------------------------------------------------------------
    # Replay Logic (Epic 3)
    # -------------------------------------------------------------------------
    async def _handle_rewind_to(self, payload: dict):
        try:
            target_utterance_id = payload.get("target_utterance_id")
            created_by = payload.get("created_by", "user")
            
            if not target_utterance_id:
                logger.error("REWIND_TO missing target_utterance_id")
                return

            logger.info(f"Planning rewind to {target_utterance_id}...")
            
            # Call Rewind Service
            plan = await self.rewind_service.create_rewind_plan(
                self.session_id, 
                self.branch_id, 
                target_utterance_id, 
                created_by
            )
            
            # Update Branch ID
            self.branch_id = plan.new_branch_id
            
            # Rewind clock to target turn end time (Ticket 7)
            # Get target turn's t_end_ms from replay_utterances[0] or from the target itself
            # The target turn is the one we are rewinding TO, so we use its end time
            target_end_ms = 0
            if plan.replay_utterances:
                # The first replay utterance comes AFTER the target, so we look at timing
                # For simplicity, estimate based on position
                # Ideally we'd have the actual t_end_ms from the target utterance
                pass  # Clock will be set to first utterance time in replay
            
            self.clock.rewind_to(target_end_ms)
            await self.broadcast_clock_rewind(target_end_ms)
            
            # Resume clock for replay (clock runs during playback)
            self.clock.resume()
            
            # Transition to REPLAYING
            self.replay_plan = plan
            await self.transition_to(ConductorState.REPLAYING)
            
        except Exception as e:
            logger.error(f"Rewind failed: {e}")
            # Stay PAUSED for now so user can try again.

    async def _run_replay_loop(self):
        logger.info("Starting REPLAY loop...")
        if not self.replay_plan:
            logger.error("No replay plan found!")
            await self.transition_to(ConductorState.LIVE)
            return
            
        replay_event_id = getattr(self.replay_plan, "replay_event_id", None)
        if replay_event_id:
            await self.replay_event_repo.update_status(replay_event_id, "replaying", first_audio_start_ts=time.time())

        total_turns = len(self.replay_plan.replay_utterances)
        
        try:
            for idx, u in enumerate(self.replay_plan.replay_utterances):
                if self.state != ConductorState.REPLAYING: break
                
                # Check for interruption
                if self.is_processing_intervention:
                    if replay_event_id:
                        await self.replay_event_repo.update_status(replay_event_id, "canceled", canceled_at_turn_id=u.utterance_id)
                    break
                
                self.current_speaker = u.speaker_id
                logger.info(f"Replaying: {u.text} (Speaker: {u.speaker_id})")
                
                # Clear event
                self.playback_done_event.clear()
                
                # Send PLAY_ASSET_CMD
                audio_url = u.audio.url if u.audio and u.audio.url else ""
                
                # Generate turn_id for this replay event
                turn_id = f"replay-{int(time.time()*1000)}"
                self.current_turn_id = turn_id
                
                if audio_url:
                    await self.send_play_asset_cmd(u.speaker_id, audio_url, u.text, turn_id)
                else:
                    await self.send_speak_cmd(u.speaker_id, u.text, None, turn_id)
                
                # Wait for PLAYBACK_DONE
                try:
                    await asyncio.wait_for(self.playback_done_event.wait(), timeout=15.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for replay playback from {u.speaker_id}")
                
                # Broadcast Progress (Ticket 5.2)
                if replay_event_id:
                    await self.broadcast_replay_progress(replay_event_id, u.utterance_id, idx + 1, total_turns)
                
                # Start speculative planning on LAST replay turn (or second-to-last if handoff)
                # so it's ready when we transition to LIVE
                is_last_turn = (idx == total_turns - 1)
                if is_last_turn and self.spec_planner:
                    logger.info(f"Starting speculative planning during last replay turn (v{self.state_version})")
                    # Build context from replay utterances
                    replay_history = [
                        f"{ru.speaker_id}: {ru.text}" 
                        for ru in self.replay_plan.replay_utterances[:idx+1]
                    ]
                    if self.spec_plan_task:
                        self.spec_plan_task.cancel()
                    self.spec_plan_task = asyncio.create_task(
                        self._run_speculative_planning(turn_id, self.state_version)
                    )
                
                await asyncio.sleep(0.5)
                
            # Loop finished or interrupted
            if self.state == ConductorState.REPLAYING:
                if replay_event_id:
                    await self.replay_event_repo.update_status(replay_event_id, "completed", last_audio_end_ts=time.time())
                
                # Check handoff reason
                if self.replay_plan.handoff_reason == "HIT_FACILITATOR_TURN":
                    logger.info("Replay finished (Hit Facilitator Turn). Handoff to LIVE.")
                else:
                    logger.info("Replay finished (End of Timeline). Handoff to LIVE.")
                
                # Transition to LIVE and start loop
                await self.transition_to(ConductorState.LIVE)
                
        except asyncio.CancelledError:
            logger.info("Replay loop cancelled")
            if replay_event_id:
                 await self.replay_event_repo.update_status(replay_event_id, "canceled")
        except Exception as e:
            logger.error(f"Replay loop error: {e}")
            await self.transition_to(ConductorState.LIVE)

    # -------------------------------------------------------------------------
    # Seed Playback (Epic 1)
    # -------------------------------------------------------------------------
    async def _run_seed_playback(self):
        try:
            logger.info("Starting seed playback...")
            view = await self.resolver.get_transcript_view(self.session_id, self.branch_id)
            seeds = [u for u in view.utterances if u.kind == "seed"]
            
            for seed in seeds:
                if self.state != ConductorState.PLAYING_SEED: break
                
                self.current_speaker = seed.speaker_id
                logger.info(f"Playing seed: {seed.text} (Speaker: {seed.speaker_id})")
                
                # Clear event before sending command
                self.playback_done_event.clear()
                
                # Send SPEAK command to the dumb agent (Task 2.1)
                audio_url = seed.audio.url if seed.audio and seed.audio.url else None
                
                # Generate turn_id
                turn_id = f"turn-{int(time.time()*1000)}"
                self.current_turn_id = turn_id
                
                await self.send_speak_cmd(seed.speaker_id, seed.text, audio_url, turn_id)
                
                # Wait for PLAYBACK_DONE (with 10s timeout fallback)
                try:
                    await asyncio.wait_for(self.playback_done_event.wait(), timeout=15.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for playback_done from {seed.speaker_id}")
                
                await asyncio.sleep(0.5) # Inter-turn pause
                
            logger.info("Seed playback complete.")
            await self.transition_to(ConductorState.LIVE)
            
        except asyncio.CancelledError:
            logger.info("Seed playback cancelled (intervention?)")
        except Exception as e:
            logger.error(f"Seed playback error: {e}")
            await self.transition_to(ConductorState.LIVE)

    # -------------------------------------------------------------------------
    # Live Loop (Epic 3)
    # -------------------------------------------------------------------------
    async def _run_live_loop(self):
        logger.info("Starting LIVE loop...")
        
        # Init LLM
        # Init LLM
        llm = LLMService()
        self.spec_planner = SpecPlanner(llm)
        
        # Initialize History Cache (Ticket 2)
        view = await self.resolver.get_transcript_view(self.session_id, self.branch_id)
        self.history_cache = [f"{u.speaker_id}: {u.text}" for u in view.utterances]
        logger.info(f"Initialized history_cache with {len(self.history_cache)} items")
        
        # Personas (Hardcoded for MVP)
        personas = {
            "alice": "You are Alice, a supportive but cautious team member. You often agree but raise risk concerns.",
            "bob": "You are Bob, an aggressive and action-oriented leader. You hate wasting time.",
            "charlie": "You are Charlie, a detail-oriented analyst. You love data but can get bogged down."
        }
        active_speakers = list(personas.keys())
        
        while self.state == ConductorState.LIVE:
            try:
                # Wait if processing intervention
                while self.is_processing_intervention:
                    await asyncio.sleep(0.1)

                # 1. Fetch Context (Ticket 2: Use Cache)
                # view = await self.resolver.get_transcript_view(self.session_id, self.branch_id)
                # history = [f"{u.speaker_id}: {u.text}" for u in view.utterances]
                history = list(self.history_cache) # Copy to be safe
                
                # 2. Plan Next Turn (Ticket 4: Speculative vs Sync)
                plan_data = None
                
                # Check if we have a valid speculative plan
                if (self.spec_plan and 
                    self.spec_plan.after_turn_id == self.current_turn_id and # Wait, current_turn_id is the *previous* turn? No, it's the one that just finished.
                    # Actually, when PLAYBACK_DONE arrives, current_turn_id is the turn that just finished.
                    # The spec plan was created *during* that turn, so its after_turn_id should match.
                    # But wait, current_turn_id is set when we send SPEAK_CMD.
                    # So when we loop around, current_turn_id is the one that just finished.
                    # Yes.
                    self.spec_plan.plan_version == self.state_version and
                    not self.is_processing_intervention):
                    
                    logger.info("Using speculative plan!")
                    # Telemetry: spec_used = True
                    plan_data = {
                        "speaker_id": self.spec_plan.speaker_id,
                        "text": self.spec_plan.text
                    }
                    # Clear it so we don't reuse
                    self.spec_plan = None
                else:
                    logger.info("Fallback to synchronous planning.")
                    # Telemetry: spec_used = False
                    plan_data = await llm.plan_next_turn(history, personas, active_speakers)
                
                speaker_id = plan_data.get("speaker_id")
                text = plan_data.get("text")
                reason = plan_data.get("reason", "Speculative" if not plan_data.get("reason") else plan_data.get("reason"))
                
                logger.info(f"Turn Plan: {speaker_id} ({reason})")
                
                # RACE CONDITION CHECK 1
                if self.is_processing_intervention:
                    logger.info("Intervention detected after planning. Discarding plan.")
                    continue
                
                if speaker_id == "silence":
                    # Broadcast Silence
                    logger.info("Loop: Silence chosen. Broadcasting silence_start...")
                    await self.broadcast_silence()
                    
                    # Wait for a while or until intervention
                    await asyncio.sleep(4.0) 
                    continue

                if speaker_id not in active_speakers:
                     logger.warning(f"LLM chose invalid speaker {speaker_id}. Skipping.")
                     await asyncio.sleep(1.0)
                     continue
                
                # Text is already generated in plan
                if not text:
                    text = "..." # Fallback?
                
                # 4. Speak
                self.current_speaker = speaker_id
                self.live_loop_signal = asyncio.Event()
                
                # Generate turn_id
                turn_id = f"turn-{int(time.time()*1000)}"
                self.current_turn_id = turn_id
                
                # Telemetry: Gap Duration
                if self.t_playback_done > 0:
                    gap_ms = (time.time() - self.t_playback_done) * 1000
                    logger.info(f"Gap Duration: {gap_ms:.2f}ms")
                
                # Spawn Speculative Planner (Ticket 4)
                # We want to plan what happens *after* this turn.
                # So we pass the history + this new turn.
                # But we can't append to history_cache yet (that happens on commit).
                # So we construct a temporary history.
                spec_history = history + [f"{speaker_id}: {text}"]
                
                if self.spec_plan_task:
                    self.spec_plan_task.cancel()
                
                self.spec_plan_task = asyncio.create_task(self._run_spec_planner(
                    spec_history, personas, active_speakers, self.state_version, turn_id
                ))
                
                await self.send_speak_cmd(speaker_id, text, audio_url=None, turn_id=turn_id)
                
                # 5. Wait for Done (with timeout)
                try:
                    await asyncio.wait_for(self.live_loop_signal.wait(), timeout=15.0)
                except asyncio.TimeoutError:
                    logger.warning("Turn timed out.")
                
                self.current_speaker = None
                self.live_loop_signal = None
                
                # 6. Commit Turn (Task 3.3)
                
                # Update Cache (Ticket 2)
                self.history_cache.append(f"{speaker_id}: {text}")
                
                # Commit with audio metadata
                audio_url = getattr(self, "last_playback_audio_url", None)
                duration_ms = getattr(self, "last_playback_duration", 0)
                
                await self._commit_ai_turn(speaker_id, text, audio_url, duration_ms)
                
                # Reset for next turn
                self.last_playback_audio_url = None
                self.last_playback_duration = 0

                # 7. Check Objectives
                if await self._check_objectives(history + [f"{speaker_id}: {text}"]):
                    logger.info("Objectives met! Ending session.")
                    break

                # Reduced Inter-turn delay (Ticket 4)
                await asyncio.sleep(0.2) # 200ms natural gap
                
            except asyncio.CancelledError:
                logger.info("Live loop cancelled")
                break
            except Exception as e:
                logger.error(f"Live loop error: {e}")
                await asyncio.sleep(2.0)

    async def _commit_ai_turn(self, identity: str, text: str, audio_url: Optional[str] = None, duration_ms: int = 0):
        if not self.writer: return
        event_id = f"urn-ai-{int(time.time()*1000)}"
        timing = {"t_start_ms": 0, "t_end_ms": duration_ms or 1000} 
        
        audio_ref = {}
        if audio_url:
            audio_ref = {
                "url": audio_url,
                "duration_ms": duration_ms
            }
        
        await self.writer.append_utterance_and_checkpoint(
            self.session_id, 
            self.branch_id, 
            "ai", 
            identity, 
            text, 
            timing, 
            {}, 
            event_id,
            audio_ref=audio_ref
        )

    async def _run_spec_planner(self, history, personas, active_speakers, version, after_turn_id):
        try:
            logger.info(f"Starting speculative plan for after {after_turn_id} (v{version})")
            plan = await self.spec_planner.plan_next(history, personas, active_speakers, version, after_turn_id)
            if plan:
                self.spec_plan = plan
                logger.info(f"Speculative plan ready: {plan.speaker_id}")
        except asyncio.CancelledError:
            logger.info("Speculative planning cancelled")
        except Exception as e:
            logger.error(f"Speculative planning error: {e}")

    async def _check_objectives(self, history: List[str]) -> bool:
        """
        Check if any session objectives are met or if we should end.
        Simple heuristic for MVP.
        """
        # Example: Keyword trigger
        if history and "wrap up" in history[-1].lower():
            return True
        return False

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------
    async def send_speak_cmd(self, participant_id: str, text: str, audio_url: Optional[str] = None, turn_id: Optional[str] = None):
        # Record timing (Ticket 2)
        t_start_ms = int(self.clock.now_ms())
        wall_start_ts = time.time()
        
        # Store pending timing for this turn
        if not hasattr(self, '_pending_turn_timing'):
            self._pending_turn_timing = {}
        if turn_id:
            self._pending_turn_timing[turn_id] = {
                "t_start_ms": t_start_ms,
                "wall_start_ts": wall_start_ts
            }
        
        cmd = AgentPacket(
            type=MsgType.SPEAK_CMD,
            session_id=self.session_id,
            turn_id=turn_id,
            payload=SpeakCmdPayload(
                text=text, 
                speaker_id=participant_id,
                audio_url=audio_url
            ).model_dump()
        )
        msg_str = cmd.model_dump_json()
        
        # Broadcast to all so frontend sees it too
        logger.info(f"Broadcasting SPEAK_CMD for {participant_id} at t={t_start_ms}ms")
        await self.room.local_participant.publish_data(
            msg_str.encode("utf-8"), 
            reliable=True, 
            destination_identities=[] # Broadcast
        )

    async def send_stop_cmd(self, participant_id: str):
        cmd = AgentPacket(
            type=MsgType.STOP_CMD,
            session_id=self.session_id
        )
        await self.room.local_participant.publish_data(
            cmd.model_dump_json().encode("utf-8"),
            reliable=True,
            destination_identities=[] # Broadcast
        )

    async def broadcast_playback_done(self, speaker_id: str):
        logger.info(f"Broadcasting PLAYBACK_DONE for {speaker_id}")
        # Notify room that speaking ended
        msg = AgentPacket(
            type=MsgType.PLAYBACK_DONE,
            session_id=self.session_id,
            payload={"speaker_id": speaker_id}
        )
        await self.room.local_participant.publish_data(
            msg.model_dump_json().encode("utf-8"),
            reliable=True,
            destination_identities=[]
        )

    async def send_play_asset_cmd(self, participant_id: str, audio_url: str, text: Optional[str] = None, turn_id: Optional[str] = None):
        # Record timing (Ticket 2)
        t_start_ms = int(self.clock.now_ms())
        wall_start_ts = time.time()
        
        if not hasattr(self, '_pending_turn_timing'):
            self._pending_turn_timing = {}
        if turn_id:
            self._pending_turn_timing[turn_id] = {
                "t_start_ms": t_start_ms,
                "wall_start_ts": wall_start_ts
            }
        
        cmd = AgentPacket(
            type=MsgType.PLAY_ASSET_CMD,
            session_id=self.session_id,
            turn_id=turn_id,
            payload=PlayAssetCmdPayload(
                audio_url=audio_url,
                speaker_id=participant_id,
                text=text,
                turn_id=turn_id
            ).model_dump()
        )
        msg_str = cmd.model_dump_json()
        
        logger.info(f"Broadcasting PLAY_ASSET_CMD for {participant_id} at t={t_start_ms}ms")
        await self.room.local_participant.publish_data(
            msg_str.encode("utf-8"), 
            reliable=True, 
            destination_identities=[] # Broadcast
        )

    async def broadcast_silence(self):
        msg = AgentPacket(
            type="silence_start", # Custom type for frontend
            session_id=self.session_id
        )
        await self.room.local_participant.publish_data(
            msg.model_dump_json().encode("utf-8"),
            reliable=True
        )

    async def broadcast_replay_progress(self, replay_event_id: str, turn_id: str, index: int, total: int):
        msg = AgentPacket(
            type=MsgType.REPLAY_PROGRESS,
            session_id=self.session_id,
            payload={
                "replay_event_id": replay_event_id,
                "turn_id": turn_id,
                "index": index,
                "total": total
            }
        )
        await self.room.local_participant.publish_data(
            msg.model_dump_json().encode("utf-8"),
            reliable=True
        )

    async def broadcast_clock_sync(self):
        """Broadcast current clock state to all clients."""
        msg = AgentPacket(
            type=MsgType.CLOCK_SYNC,
            session_id=self.session_id,
            payload=self.clock.to_sync_payload()
        )
        await self.room.local_participant.publish_data(
            msg.model_dump_json().encode("utf-8"),
            reliable=True
        )
        logger.info(f"Broadcast CLOCK_SYNC: {self.clock.to_sync_payload()}")

    async def broadcast_clock_pause(self, session_time_ms: float):
        """Broadcast clock pause to all clients."""
        msg = AgentPacket(
            type=MsgType.CLOCK_PAUSE,
            session_id=self.session_id,
            payload={"session_time_ms": session_time_ms}
        )
        await self.room.local_participant.publish_data(
            msg.model_dump_json().encode("utf-8"),
            reliable=True
        )

    async def broadcast_clock_resume(self, session_time_ms: float):
        """Broadcast clock resume to all clients."""
        msg = AgentPacket(
            type=MsgType.CLOCK_RESUME,
            session_id=self.session_id,
            payload={"session_time_ms": session_time_ms}
        )
        await self.room.local_participant.publish_data(
            msg.model_dump_json().encode("utf-8"),
            reliable=True
        )

    async def broadcast_clock_rewind(self, target_ms: float):
        """Broadcast clock rewind to all clients."""
        msg = AgentPacket(
            type=MsgType.CLOCK_REWIND,
            session_id=self.session_id,
            payload={"session_time_ms": target_ms}
        )
        await self.room.local_participant.publish_data(
            msg.model_dump_json().encode("utf-8"),
            reliable=True
        )

    # -------------------------------------------------------------------------
    # Connection handling
    # -------------------------------------------------------------------------
    def on_participant_disconnected(self, participant: rtc.RemoteParticipant):
        pass

    def on_track_subscribed(self, track: rtc.RemoteTrack, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        logger.info(f"DEBUG: Track subscribed: {participant.identity} kind={track.kind}")
        if track.kind == rtc.TrackKind.KIND_AUDIO:
             # Heuristic: if it's not a bot, it's a human (facilitator)
             if participant.identity not in ["alice", "bob", "charlie", "conductor-bot"]:
                logger.info(f"Subscribed to audio track for {participant.identity}")
                
                # Task 1.4: Send Server Confirmation (Mic Seen)
                asyncio.create_task(self._send_mic_seen(participant.identity))
                # Note: Legacy STT Logic removed. Worker handles transcription.

    async def _send_mic_seen(self, participant_id: str):
        msg = AgentPacket(
            type=MsgType.MIC_SEEN,
            session_id=self.session_id,
            payload={"participant_id": participant_id}
        )
        try:
             await self.room.local_participant.publish_data(
                msg.model_dump_json().encode("utf-8"),
                reliable=True,
                destination_identities=[participant_id]
            )
        except Exception as e:
            logger.error(f"Failed to send MIC_SEEN: {e}")

    # -------------------------------------------------------------------------
    # Transcription Handling (Epic 2)
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Transcription Handling (Epic 2)
    # -------------------------------------------------------------------------
    def _handle_transcript_complete(self, payload: dict):
        # Triggered by MsgType.TRANSCRIPT_COMPLETE from Worker
        asyncio.create_task(self._process_transcript_and_resume(payload))
        
    async def _process_transcript_and_resume(self, payload: dict):
        text = payload.get("text", "")
        speaker_id = payload.get("speaker_id", "user")
        
        logger.info(f"Conductor handling transcript from {speaker_id}: {text}")
        
        if not text: 
            # Even if empty, we should resume the loop
            self.is_processing_intervention = False
            return

        # 1. Commit to DB (Wait for it!)
        # Crucial: We must wait for this to complete so the next fetch sees it.
        
        # Update Cache (Ticket 2)
        self.history_cache.append(f"{speaker_id}: {text}")
        self.state_version += 1 # Invalidate any stale plans
        
        await self._commit_user_turn(speaker_id, text)
        
        # 2. Notify Live Loop to proceed
        logger.info("Facilitator intervention complete. Resuming live loop.")
        self.is_processing_intervention = False
            
    async def _commit_user_turn(self, identity: str, text: str):
        if not self.writer: return
        
        timing = {"t_start_ms": 0, "t_end_ms": 1000} # Stub timing
        event_id = f"urn-{int(time.time()*1000)}"
        
        try:
            logger.info(f"Committing facilitator turn: {text}")
            await self.writer.append_utterance_and_checkpoint(
                self.session_id, 
                self.branch_id, 
                "user_intervention", 
                identity, 
                text, 
                timing, 
                {}, 
                event_id
            )
        except Exception as e:
            logger.error(f"Failed to commit user turn: {e}")
            
    async def _send_fac_ack(self, participant_id: str):
        msg = AgentPacket(
            type=MsgType.FAC_ACK,
            session_id=self.session_id,
            payload={"participant_id": participant_id} 
        )
        try:
             await self.room.local_participant.publish_data(
                msg.model_dump_json().encode("utf-8"),
                reliable=True,
                destination_identities=[participant_id] # Targeted ACK
            )
        except Exception as e:
            logger.error(f"Failed to send FAC_ACK: {e}")

    # _finalize_recording removed (Logic moved to Worker)
