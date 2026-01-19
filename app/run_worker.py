import asyncio
import os
import logging
from dotenv import load_dotenv
from app.transcription.worker import TranscriptionWorker
from app.domain.services.stt_service import STTService

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker_main")

async def main():
    logger.info("Starting Transcription Worker...")
    
    # Config
    url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    api_key = os.getenv("LIVEKIT_API_KEY", "devkey")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")
    
    # LIVEKIT_TOKEN should be generated or we can generate one here for the "transcription-bot"
    # For now, let's assume we use the same helper or just generate one.
    # Actually, we need a helper to generate a token for the bot.
    
    from livekit import api
    token_verifier = api.AccessToken(api_key, api_secret) \
        .with_identity("transcription-bot") \
        .with_name("Transcription Bot") \
        .with_grants(api.VideoGrants(room_join=True, room="case_study_1")) # Hardcoded room for now? 
        # Ideally the Worker connects dynamically or we have one worker per room.
        # For MVP, let's connect to "case_study_1" or pass as arg.
    
    token = token_verifier.to_jwt()
    
    stt = STTService()
    worker = TranscriptionWorker(stt)
    
    try:
        await worker.connect(url, token)
        logger.info("Worker Running. Press Ctrl+C to exit.")
        # Keep alive
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await worker.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
