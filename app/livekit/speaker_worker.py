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
import os
import logging
import time
import traceback
from livekit import rtc
from typing import Optional

from app.livekit.protocol import AgentPacket, MsgType, SpeakCmdPayload, PlaybackDonePayload

logger = logging.getLogger(__name__)

class SpeakerWorker:
    """
    Dumb speaker client. 
    Connects to LiveKit, listens for SPEAK_CMD, plays TTS, sends PLAYBACK_DONE.
    """
    def __init__(self, identity: str, voice_settings: dict = None):
        self.identity = identity
        self.voice_settings = voice_settings or {}
        self.room = rtc.Room()
        self.room.on("data_received", self.on_data_received)
        
        self.audio_source = rtc.AudioSource(24000, 1)
        self.track = rtc.LocalAudioTrack.create_audio_track("speaker-mic", self.audio_source)
        
        # TTS Plugin
        try:
            from app.livekit.tts import get_tts_plugin
            self.tts = get_tts_plugin("openai", **self.voice_settings) # Pass voice config
        except Exception as e:
            logger.error(f"Failed to load TTS plugin: {e}")
            self.tts = None

        self.speak_task: Optional[asyncio.Task] = None
        self.session_id: Optional[str] = None
        self.current_turn_id: Optional[str] = None

    async def connect(self, url: str, token: str):
        await self.room.connect(url, token)
        await self.room.local_participant.publish_track(self.track)
        logger.info(f"Speaker {self.identity} connected and published track")

    async def disconnect(self):
        await self.room.disconnect()

    def on_data_received(self, event):
        try:
            # Extract fields from event object
            data = event.data
            participant = event.participant
            
            payload_str = data.decode("utf-8")
            raw_msg = json.loads(payload_str)
            
            # Basic validation
            try:
                packet = AgentPacket(**raw_msg)
            except Exception:
                # Might be legacy message or noise
                return

            if packet.type == MsgType.SPEAK_CMD:
                # Check destination or speaker_id
                # (LiveKit usually filters destination for us if sent privately, 
                # but good to check if it matches our identity if payload specifies it)
                cmd = SpeakCmdPayload(**packet.payload)
                if cmd.speaker_id == self.identity:
                    self.session_id = packet.session_id
                    self.current_turn_id = packet.turn_id
                    self._handle_speak_cmd(cmd)
            
            elif packet.type == MsgType.STOP_CMD:
                self._handle_stop_cmd()

        except Exception as e:
            logger.error(f"Error handling data in {self.identity}: {e}")
            traceback.print_exc()

    def _handle_speak_cmd(self, cmd: SpeakCmdPayload):
        if self.speak_task:
            self.speak_task.cancel()
        
        self.speak_task = asyncio.create_task(self._speak_routine(cmd))

    def _handle_stop_cmd(self):
        logger.info(f"Speaker {self.identity} received STOP_CMD")
        if self.speak_task:
            self.speak_task.cancel()
            # We should probably report PLAYBACK_STOPPED? 
            # For now, just stop.

    async def _speak_routine(self, cmd: SpeakCmdPayload):
        start_time = time.time()
        logger.info(f"Speaker {self.identity} starting: {cmd.text[:30]}...")
        
        try:
            # 1. Check for audio file (Pre-recorded)
            if hasattr(cmd, 'audio_url') and cmd.audio_url and os.path.exists(cmd.audio_url):
                 logger.info(f"Playing audio file: {cmd.audio_url}")
                 await self._play_audio_file(cmd.audio_url)
            
            # 2. Fallback to TTS (On-the-fly)
            elif self.tts:
                async for audio_chunk in self.tts.synthesize(cmd.text):
                    # SynthesizedAudio wraps the actual data in 'frame' property typically, or 'data'
                    # Based on error, audio_chunk is SynthesizedAudio.
                    # Try accessing .frame (standard for livekit agents) or .data
                    if hasattr(audio_chunk, 'frame'):
                        await self.audio_source.capture_frame(audio_chunk.frame)
                    elif hasattr(audio_chunk, 'data'):
                         await self.audio_source.capture_frame(audio_chunk.data)
                    else:
                        # Fallback: maybe it IS the frame (but error says no)
                        await self.audio_source.capture_frame(audio_chunk)
            else:
                 logger.warning("No TTS plugin available and no audio file")
                 return
            
            # Finished
            duration_ms = int((time.time() - start_time) * 1000)
            await self._send_done(duration_ms)
            
        except asyncio.CancelledError:
            logger.info(f"Speaker {self.identity} audio cancelled")
        except Exception as e:
            logger.error(f"Speaker {self.identity} error: {e}")

    async def _play_audio_file(self, filepath: str):
        # Requires ffmpeg installed
        try:
             # Basic FFmpeg decoding to PCM 24k mono s16le
             process = await asyncio.create_subprocess_exec(
                 "ffmpeg", "-i", filepath, "-f", "s16le", "-ac", "1", "-ar", "24000", "-",
                 stdout=asyncio.subprocess.PIPE,
                 stderr=asyncio.subprocess.DEVNULL
             )
             
             while True:
                 data = await process.stdout.read(960) # 20ms frame (24000 * 2 * 0.02) = 960 bytes
                 if not data: break
                 
                 frame = rtc.AudioFrame(
                    data=data,
                    sample_rate=24000,
                    num_channels=1,
                    samples_per_channel=len(data) // 2
                 )
                 await self.audio_source.capture_frame(frame)
                 await asyncio.sleep(0.019) # Slightly faster than realtime
                 
             await process.wait()
        except Exception as e:
             logger.error(f"File playback error: {e}")

    async def _send_done(self, duration_ms: int):
        if not self.session_id: return
        
        payload = PlaybackDonePayload(
            speaker_id=self.identity,
            duration_ms=duration_ms,
            interrupted=False
        )
        msg = AgentPacket(
            type=MsgType.PLAYBACK_DONE,
            session_id=self.session_id,
            turn_id=self.current_turn_id,
            payload=payload.model_dump()
        )
        
        await self.room.local_participant.publish_data(
            msg.model_dump_json().encode("utf-8"),
            reliable=True
        )
