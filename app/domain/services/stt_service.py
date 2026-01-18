import logging
import io
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
             logger.warning("OPENAI_API_KEY not set. STT will fail.")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        """
        Transcribe audio bytes using OpenAI Whisper.
        """
        try:
            # Create a virtual file for the API
            # OpenAI requires a 'name' attribute for the file-like object to guess mime type
            file_obj = io.BytesIO(audio_data)
            file_obj.name = f"audio.{format}"
            
            logger.info(f"Sending STT request for {len(audio_data)} bytes...")
            
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=file_obj,
                response_format="text"
            )
            
            # The response_format="text" returns a raw string
            text = transcript.strip() if isinstance(transcript, str) else transcript.text
            
            logger.info(f"STT Result: {text}")
            return text
            
        except Exception as e:
            logger.error(f"STT Error: {e}")
            return ""
