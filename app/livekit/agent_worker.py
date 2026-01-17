import asyncio
import json
import logging
from livekit import rtc
from typing import Optional

logger = logging.getLogger(__name__)

class AgentWorker:
    def __init__(self, identity: str, persona: str):
        self.identity = identity
        self.persona = persona
        self.room = rtc.Room()
        self.room.on("data_received", self.on_data_received)
        self.is_speaking = False
        
        # Audio setup
        self.audio_source = rtc.AudioSource(24000, 1) # 24kHz mono (standard for TTS)
        self.track = rtc.LocalAudioTrack.create_audio_track("agent-mic", self.audio_source)
        
        # TTS Plugin
        from app.livekit.tts import get_tts_plugin
        self.tts = get_tts_plugin("openai") # Default to OpenAI

    async def connect(self, url: str, token: str):
        await self.room.connect(url, token)
        # Publish the audio track
        await self.room.local_participant.publish_track(self.track)
        logger.info(f"Agent {self.identity} connected and published track")

    async def disconnect(self):
        await self.room.disconnect()

    def on_data_received(self, data: bytes, participant: rtc.RemoteParticipant, kind: rtc.DataPacketKind):
        try:
            msg = json.loads(data.decode("utf-8"))
            if msg.get("type") == "grant_floor":
                if msg.get("identity") == self.identity:
                    self.on_floor_granted()
        except Exception as e:
            logger.error(f"Error handling data: {e}")

    def on_floor_granted(self):
        logger.info(f"Agent {self.identity} granted floor")
        # In a real scenario, we would generate text from LLM here.
        # For now, we use a stub text.
        asyncio.create_task(self.speak("Hello, I am speaking now."))

    async def speak(self, text: str):
        self.is_speaking = True
        logger.info(f"Agent {self.identity} speaking: {text}")
        
        try:
            # Generate audio stream
            async for audio_frame in self.tts.synthesize(text):
                # Capture frame to source
                await self.audio_source.capture_frame(audio_frame)
            
        except Exception as e:
            logger.error(f"TTS Error: {e}")
        
        # Done
        self.is_speaking = False
        msg = json.dumps({"type": "done"})
        await self.room.local_participant.publish_data(msg.encode("utf-8"), reliable=True)

    async def bid(self):
        logger.info(f"Agent {self.identity} bidding")
        msg = json.dumps({"type": "bid", "text": "I have something to say"})
        await self.room.local_participant.publish_data(msg.encode("utf-8"), reliable=True)
