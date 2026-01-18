
import sys
import traceback
import os
from dotenv import load_dotenv

# Try to replicate the environment setup
load_dotenv(".env.local")

print(f"Python version: {sys.version}")

try:
    print("Attempting to import livekit.plugins.openai...")
    from livekit.plugins import openai
    print("SUCCESS: imported livekit.plugins.openai")
except Exception:
    print("FAILED: imported livekit.plugins.openai")
    traceback.print_exc()

try:
    print("\nAttempting to import livekit.plugins.elevenlabs...")
    from livekit.plugins import elevenlabs
    print("SUCCESS: imported livekit.plugins.elevenlabs")
except Exception:
    print("FAILED: imported livekit.plugins.elevenlabs")
    traceback.print_exc()

try:
    print("\nAttempting to initialize OpenAI TTS...")
    tts = openai.TTS()
    print("SUCCESS: initialized OpenAI TTS")
except Exception:
    print("FAILED: initialized OpenAI TTS")
    traceback.print_exc()
