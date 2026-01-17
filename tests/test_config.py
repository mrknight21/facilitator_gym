import os
import pytest

# Set env vars before importing app.core.config to pass validation
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["LIVEKIT_URL"] = "ws://localhost:7880"
os.environ["LIVEKIT_API_KEY"] = "devkey"
os.environ["LIVEKIT_API_SECRET"] = "secret"

from app.core.config import settings

def test_config_loads():
    assert settings.MONGO_URI == "mongodb://localhost:27017"
    assert settings.MONGO_DB == "sim"
