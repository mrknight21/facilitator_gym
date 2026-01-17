from livekit.agents import stt
from livekit.plugins import openai
import logging

logger = logging.getLogger(__name__)

def get_stt_plugin() -> stt.STT:
    """
    Returns the configured STT plugin.
    Currently defaults to OpenAI Whisper.
    """
    try:
        return openai.STT()
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI STT: {e}")
        raise
