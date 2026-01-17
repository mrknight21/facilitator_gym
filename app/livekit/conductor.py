import asyncio
import json
import logging
import time
from livekit import rtc
from typing import Dict, List, Optional
from app.domain.services.conductor_writer import ConductorWriter
from app.metrics.engine import MetricsEngine
from app.domain.services.transcript_resolver import TranscriptResolver

logger = logging.getLogger(__name__)

class Conductor:
    def __init__(self, writer: ConductorWriter, metrics_engine: MetricsEngine, resolver: TranscriptResolver):
        self.writer = writer
        self.metrics_engine = metrics_engine
        self.resolver = resolver
        self.room = rtc.Room()
        self.bid_queue: List[Dict] = []
        self.current_speaker: Optional[str] = None
        self.session_id: Optional[str] = None
        self.branch_id: Optional[str] = None
        self.is_playing_seeds = False
        self.seed_task = None
        
        self.room.on("data_received", self.on_data_received)
        self.room.on("participant_disconnected", self.on_participant_disconnected)
        self.room.on("track_subscribed", self.on_track_subscribed)

        # STT Setup
        from app.livekit.stt import get_stt_plugin
        self.stt = get_stt_plugin()
        self.stt_streams = {} # identity -> task

    async def connect(self, url: str, token: str, session_id: str, branch_id: str):
        self.session_id = session_id
        self.branch_id = branch_id
        await self.room.connect(url, token)
        logger.info(f"Conductor connected to room {self.room.name}")

    async def disconnect(self):
        await self.room.disconnect()
        await self.stop_seed_playback()
        # Cancel all STT tasks
        for task in self.stt_streams.values():
            task.cancel()

    def on_data_received(self, data: bytes, participant: rtc.RemoteParticipant, kind: rtc.DataPacketKind):
        try:
            msg = json.loads(data.decode("utf-8"))
            msg_type = msg.get("type")
            
            if msg_type == "bid":
                # Intervention stops seeds
                if self.is_playing_seeds:
                    asyncio.create_task(self.stop_seed_playback())
                self.handle_bid(participant.identity, msg)
            elif msg_type == "done":
                asyncio.create_task(self.handle_done(participant.identity))
                
        except Exception as e:
            logger.error(f"Error handling data: {e}")

    def on_participant_disconnected(self, participant: rtc.RemoteParticipant):
        self.bid_queue = [b for b in self.bid_queue if b["identity"] != participant.identity]
        if self.current_speaker == participant.identity:
            self.current_speaker = None
            self.process_queue()
        
        # Cleanup STT
        if participant.identity in self.stt_streams:
            self.stt_streams[participant.identity].cancel()
            del self.stt_streams[participant.identity]

    def on_track_subscribed(self, track: rtc.RemoteTrack, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if track.kind == rtc.TrackKind.KIND_AUDIO and participant.identity not in ["alice", "bob", "charlie", "conductor-bot"]:
            logger.info(f"Subscribed to audio from {participant.identity}, starting STT")
            task = asyncio.create_task(self._handle_speech(participant, track))
            self.stt_streams[participant.identity] = task

    async def _handle_speech(self, participant: rtc.RemoteParticipant, track: rtc.RemoteAudioTrack):
        audio_stream = rtc.AudioStream(track)
        stt_stream = self.stt.stream()
        
        async def push_audio():
            async for frame in audio_stream:
                stt_stream.push_frame(frame)
            stt_stream.end_input()

        async def read_transcripts():
            from livekit.agents import stt
            async for event in stt_stream:
                if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                    text = event.alternatives[0].text
                    if text:
                        logger.info(f"STT from {participant.identity}: {text}")
                        await self.handle_intervention(participant.identity, text)

        try:
            await asyncio.gather(push_audio(), read_transcripts())
        except Exception as e:
            logger.error(f"STT Error for {participant.identity}: {e}")

    async def handle_intervention(self, identity: str, text: str):
        logger.info(f"Intervention detected from {identity}: {text}")
        
        # 1. Stop everything
        if self.is_playing_seeds:
            await self.stop_seed_playback()
        
        # 2. Revoke floor from current speaker (if any)
        # For now, we just rely on them stopping naturally or we could send a "stop" message
        # But let's just log it for now as the "Intervention" logic in F006 was mostly client-side API.
        # Here we are doing it server-side.
        
        # TODO: Call the actual intervention logic (forking, etc)
        # This would duplicate what the /intervene API does.
        # Ideally, we refactor the logic from the API into a service method we can call here.
        pass

    def handle_bid(self, identity: str, msg: Dict):
        logger.info(f"Received bid from {identity}: {msg}")
        self.bid_queue.append({"identity": identity, "msg": msg})
        self.process_queue()

    async def handle_done(self, identity: str):
        logger.info(f"Received done from {identity}")
        if self.current_speaker == identity:
            await self.capture_turn(identity)
            self.current_speaker = None
            self.process_queue()

    async def capture_turn(self, identity: str):
        if not self.session_id or not self.branch_id:
            logger.error("Missing session context")
            return

        text = "Stub text from speech"
        timing = {"t_start_ms": 0, "t_end_ms": 1000}
        state = {}
        event_id = f"turn-{identity}-{int(time.time())}"
        
        try:
            res = await self.writer.append_utterance_and_checkpoint(
                self.session_id, self.branch_id, "ai", identity, text, timing, state, event_id
            )
            
            await self.metrics_engine.compute_for_checkpoint(
                self.session_id, self.branch_id, res["checkpoint_id"]
            )
            logger.info(f"Captured turn for {identity}")
            
        except Exception as e:
            logger.error(f"Failed to capture turn: {e}")

    def process_queue(self):
        if self.current_speaker:
            return
        
        if not self.bid_queue:
            return
            
        next_bid = self.bid_queue.pop(0)
        identity = next_bid["identity"]
        
        self.grant_floor(identity)

    def grant_floor(self, identity: str):
        logger.info(f"Granting floor to {identity}")
        self.current_speaker = identity
        
        msg = json.dumps({"type": "grant_floor", "identity": identity})
        asyncio.create_task(self.room.local_participant.publish_data(msg.encode("utf-8"), reliable=True))

    async def start_seed_playback(self):
        self.is_playing_seeds = True
        self.seed_task = asyncio.create_task(self._play_seeds_loop())

    async def stop_seed_playback(self):
        self.is_playing_seeds = False
        if self.seed_task:
            self.seed_task.cancel()
            try:
                await self.seed_task
            except asyncio.CancelledError:
                pass

    async def _play_seeds_loop(self):
        try:
            view = await self.resolver.get_transcript_view(self.session_id, self.branch_id)
            seeds = [u for u in view.utterances if u.kind == "seed"]
            
            for seed in seeds:
                if not self.is_playing_seeds:
                    break
                
                logger.info(f"Playing seed {seed.display_id}: {seed.text}")
                duration = (seed.timing.t_end_ms - seed.timing.t_start_ms) / 1000.0
                if duration <= 0: duration = 0.1 # Fast for tests
                
                await asyncio.sleep(duration)
                
            logger.info("Seed playback finished")
        except Exception as e:
            logger.error(f"Error in seed playback: {e}")
        finally:
            self.is_playing_seeds = False
