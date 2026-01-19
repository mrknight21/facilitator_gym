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

    async def transcribe(self, audio_data: bytes, format: str = "wav", model: str = "whisper-1") -> str:
        """
        Transcribe audio bytes using OpenAI Whisper or GPT-4o.
        """
        try:
            logger.info(f"Sending STT request for {len(audio_data)} bytes using {model}...")
            
            # Heuristic: If it's a "chat" model or "audio-preview" (multimodal), use Chat API.
            # If it's "whisper" or "transcribe", use Audio API.
            if "gpt-4o" in model and "preview" in model:
                # Use Multimodal Chat API (gpt-4o-audio-preview)
                import base64
                b64_audio = base64.b64encode(audio_data).decode("utf-8")
                
                response = await self.client.chat.completions.create(
                    model=model, 
                    modalities=["text"],
                    temperature=0.0, # Minimize creativity
                    messages=[
                        {
                           "role": "system",
                           "content": "You are a transcription engine. Your only task is to transcribe the user's audio verbatim. If the audio contains no speech, is just background noise, or is unintelligible, output exactly: [SILENCE]. Do not attempt to complete sentences or generate a response."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Transcribe the audio."},
                                {
                                    "type": "input_audio", 
                                    "input_audio": {
                                        "data": b64_audio,
                                        "format": "wav"
                                    }
                                }
                            ]
                        }
                    ]
                )
                text = response.choices[0].message.content
                logger.info(f"GPT-4o Transcript: {text}")
                
                if text and "[SILENCE]" in text:
                    return ""
                
                return text or ""

            else:
                # Use Standard Whisper / Transcription API (whisper-1, gpt-4o-transcribe)
                # Create a virtual file for the API
                file_obj = io.BytesIO(audio_data)
                file_obj.name = f"audio.{format}"
                
                transcript = await self.client.audio.transcriptions.create(
                    model=model, 
                    file=file_obj,
                    response_format="text",
                    prompt="Facilitator guiding a corporate training session." # Hint to reduce hallucination
                )
                
                # The response_format="text" returns a raw string
                text = transcript.strip() if isinstance(transcript, str) else transcript.text
                
                logger.info(f"STT Result: {text}")
                return text
            
        except Exception as e:
            logger.error(f"STT Error: {e}")
            return ""
