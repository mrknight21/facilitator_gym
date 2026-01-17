import pytest
from app.livekit.tokens import build_room_name, mint_token

def test_build_room_name():
    assert build_room_name("123") == "sess-123"

def test_mint_token():
    # This might fail if keys are invalid format for JWT signing
    # But "devkey" and "secret" are usually fine for local dev.
    token = mint_token("user", "room1", True, True, True)
    assert isinstance(token, str)
    assert len(token) > 0
