import pytest
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.livekit.agent_worker import AgentWorker

@pytest.fixture
def mock_room():
    room = MagicMock()
    room.on = MagicMock()
    room.local_participant.publish_data = AsyncMock()
    return room

@pytest.fixture
def agent(mock_room):
    with pytest.MonkeyPatch.context() as m:
        m.setattr("livekit.rtc.Room", lambda: mock_room)
        m.setattr("app.livekit.tts.get_tts_plugin", lambda *args: MagicMock(synthesize=lambda text: AsyncMock(return_value=iter([]))()))
        m.setattr("livekit.rtc.AudioSource", MagicMock)
        
        mock_track_cls = MagicMock()
        mock_track_cls.create_audio_track = MagicMock()
        m.setattr("livekit.rtc.LocalAudioTrack", mock_track_cls)
        
        # Mock the async iterator for synthesize
        mock_tts = MagicMock()
        async def mock_synthesize(text):
            yield MagicMock()
        mock_tts.synthesize = mock_synthesize
        m.setattr("app.livekit.tts.get_tts_plugin", lambda *args: mock_tts)

        a = AgentWorker("alice", "persona")
        a.room = mock_room
        return a

@pytest.mark.asyncio
async def test_agent_speaks_on_grant(agent, mock_room):
    # Simulate grant floor
    msg = json.dumps({"type": "grant_floor", "identity": "alice"}).encode("utf-8")
    
    # Trigger callback
    agent.on_data_received(msg, None, None)
    
    # Wait for async task
    await asyncio.sleep(0.2)
    
    # Verify done message sent
    mock_room.local_participant.publish_data.assert_called()
    call_args = mock_room.local_participant.publish_data.call_args
    data = json.loads(call_args[0][0].decode("utf-8"))
    assert data["type"] == "done"

@pytest.mark.asyncio
async def test_agent_ignores_grant_for_others(agent, mock_room):
    msg = json.dumps({"type": "grant_floor", "identity": "bob"}).encode("utf-8")
    agent.on_data_received(msg, None, None)
    await asyncio.sleep(0.1)
    mock_room.local_participant.publish_data.assert_not_called()
