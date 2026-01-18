import sys
import typing

# Python 3.9 Compatibility Patch
if sys.version_info < (3, 10):
    try:
        from typing_extensions import TypeAlias
        typing.TypeAlias = TypeAlias
    except ImportError:
        pass

from livekit.agents import tts
from livekit.plugins import openai, elevenlabs
import logging
import os

logger = logging.getLogger(__name__)

def get_tts_plugin(provider: str = "openai", **kwargs) -> tts.TTS:
    """
    Returns the configured TTS plugin.
    Args:
        provider: "openai" or "elevenlabs"
        **kwargs: API-specific options (e.g. voice="alloy")
    """
    try:
        if provider == "elevenlabs":
            return elevenlabs.TTS(**kwargs)
        else:
            return openai.TTS(**kwargs)
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Failed to initialize {provider} TTS: {e}")
        raise
