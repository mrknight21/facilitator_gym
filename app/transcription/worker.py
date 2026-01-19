import asyncio
import logging
import json
import wave
import io
import time
from livekit import rtc
from app.livekit.protocol import MsgType, AgentPacket
from app.domain.services.stt_service import STTService

logger = logging.getLogger(__name__)

class TranscriptionWorker:
    def __init__(self, stt_service: STTService):
        self.room = rtc.Room()
        self.stt_service = stt_service
        
        # State
        self.is_recording = False
        self.audio_capture_buffer = bytearray()
        self.last_sample_rate = 48000
        self.current_speaker_id = None
        
        # Audio Stream Task
        self.audio_stream_task = None

        # Event handlers
        self.room.on("data_received", self.on_data_received)
        self.room.on("track_subscribed", self.on_track_subscribed)
    
    async def connect(self, url: str, token: str):
        await self.room.connect(url, token)
        logger.info(f"TranscriptionWorker connected to room {self.room.name}")

    async def disconnect(self):
        await self.room.disconnect()

    def on_data_received(self, event):
        try:
            payload_str = event.data.decode("utf-8")
            raw_msg = json.loads(payload_str)
            packet = AgentPacket(**raw_msg)
            
            if packet.type == MsgType.FAC_START:
                self.start_recording(event.participant.identity)
            elif packet.type == MsgType.FAC_END:
                # We assume the sender of FAC_END is the one recording
                if self.current_speaker_id == event.participant.identity:
                    asyncio.create_task(self.stop_recording_and_transcribe())
        except Exception as e:
            logger.error(f"Worker Error handling data: {e}")

    def on_track_subscribed(self, track: rtc.RemoteTrack, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
             # We listen to everyone (or filter known bots). 
             # For PTT, we only buffer when `is_recording` is True for that user.
             # Ideally we have map<UserId, Task>. For MVP single user:
             if participant.identity not in ["conductor-bot"]:
                 logger.info(f"Subscribed to audio track from {participant.identity}. Starting stream handler.")
                 self.audio_stream_task = asyncio.create_task(self._handle_audio_stream(track, participant.identity))

    async def _handle_audio_stream(self, track: rtc.RemoteAudioTrack, identity: str):
        stream = rtc.AudioStream(track)
        frame_count = 0
        async for event in stream:
            # Debug log periodically to prove flow
            frame_count += 1
            if frame_count % 100 == 0:
                logger.debug(f"Received 100 frames from {identity}. is_recording={self.is_recording}")
            
            # Fix for mixing audio: Only capture if this is the active speaker (Facilitator)
            if self.is_recording and identity == self.current_speaker_id:
                self.audio_capture_buffer.extend(event.frame.data)
                self.last_sample_rate = event.frame.sample_rate
                self.last_num_channels = event.frame.num_channels

    def start_recording(self, identity: str):
        logger.info(f"Worker started recording {identity}")
        self.is_recording = True
        self.current_speaker_id = identity
        self.audio_capture_buffer.clear()
        self.last_sample_rate = 48000 # Default
        self.last_num_channels = 1   # Default

    async def stop_recording_and_transcribe(self):
        logger.info("Worker stop recording. Transcribing...")
        self.is_recording = False
        speaker_id = self.current_speaker_id
        
        if not self.audio_capture_buffer:
            logger.warning("No audio captured.")
            return

        try:
            # 1. WAV Encoding
            buffer_bytes = bytes(self.audio_capture_buffer)
            logger.info(f"Encoding WAV: Rate={self.last_sample_rate}, Channels={self.last_num_channels}, Bytes={len(buffer_bytes)}")
            
            with io.BytesIO() as wav_io:
                with wave.open(wav_io, "wb") as wav_file:
                    wav_file.setnchannels(self.last_num_channels)
                    wav_file.setsampwidth(2) 
                    wav_file.setframerate(self.last_sample_rate)
                    wav_file.writeframes(buffer_bytes)
                wav_bytes = wav_io.getvalue()

            # 2. Transcribe
            # text = await self.stt_service.transcribe(wav_bytes)
            # Switch to GPT-4o Audio Preview for better quality?
            text = await self.stt_service.transcribe(wav_bytes, model="gpt-4o-transcribe")
            logger.info(f"Transcript: {text}")

            # 3. Publish Result
            # We assume a new MsgType for this? Or just log for now?
            # Goal is 'TRANSCRIPT_COMPLETE'
            # Let's add it to protocol? Or just use a generic payload for now.
            if text:
                await self._publish_transcript(speaker_id, text)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
        finally:
            self.audio_capture_buffer.clear()
            self.current_speaker_id = None

    async def _publish_transcript(self, speaker_id: str, text: str):
        # We need a message type for this.
        # Let's define it in protocol first, but for now we'll stub "transcript_complete" string
        msg = {
            "type": "transcript_complete",
            "session_id": "unknown", # payload
            "payload": {
                "speaker_id": speaker_id,
                "text": text
            }
        }
        await self.room.local_participant.publish_data(
            json.dumps(msg).encode("utf-8"),
            reliable=True
        )
