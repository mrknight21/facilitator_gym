from livekit.agents import tts
from livekit.plugins import openai, elevenlabs
import logging
import os

logger = logging.getLogger(__name__)

def get_tts_plugin(provider: str = "openai") -> tts.TTS:
    """
    Returns the configured TTS plugin.
    Args:
        provider: "openai" or "elevenlabs"
    """
    try:
        if provider == "elevenlabs":
            return elevenlabs.TTS()
        else:
            return openai.TTS()
    except Exception as e:
        logger.error(f"Failed to initialize {provider} TTS: {e}")
        raise
