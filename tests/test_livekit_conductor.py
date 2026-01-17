import pytest
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.livekit.conductor import Conductor
from app.domain.schemas import UtteranceView, Timing

@pytest.fixture
def mock_room():
    room = MagicMock()
    room.on = MagicMock()
    room.local_participant.publish_data = AsyncMock()
    return room

@pytest.fixture
def mock_writer():
    writer = AsyncMock()
    writer.append_utterance_and_checkpoint.return_value = {"checkpoint_id": "cp1"}
    return writer

@pytest.fixture
def mock_metrics():
    metrics = AsyncMock()
    return metrics

@pytest.fixture
def mock_resolver():
    resolver = AsyncMock()
    class View:
        utterances = [
            UtteranceView(
                utterance_id="u1", speaker_id="s1", kind="seed", text="seed1", display_id="1",
                timing=Timing(t_start_ms=0, t_end_ms=100)
            ),
            UtteranceView(
                utterance_id="u2", speaker_id="s2", kind="seed", text="seed2", display_id="2",
                timing=Timing(t_start_ms=100, t_end_ms=200)
            )
        ]
    resolver.get_transcript_view.return_value = View()
    return resolver

@pytest.fixture
def conductor(mock_room, mock_writer, mock_metrics, mock_resolver):
    with pytest.MonkeyPatch.context() as m:
        m.setattr("livekit.rtc.Room", lambda: mock_room)
        c = Conductor(mock_writer, mock_metrics, mock_resolver)
        c.room = mock_room
        c.session_id = "s1"
        c.branch_id = "b1"
        return c

@pytest.mark.asyncio
async def test_seed_playback(conductor, mock_resolver):
    await conductor.start_seed_playback()
    
    # Wait for loop
    await asyncio.sleep(0.3)
    
    assert conductor.is_playing_seeds is False # Should finish
    mock_resolver.get_transcript_view.assert_called_once()

@pytest.mark.asyncio
async def test_interruption(conductor, mock_resolver):
    await conductor.start_seed_playback()
    
    # Simulate bid (interruption)
    msg = json.dumps({"type": "bid"}).encode("utf-8")
    conductor.on_data_received(msg, MagicMock(identity="user"), None)
    
    # Wait for cancel
    await asyncio.sleep(0.1)
    
    assert conductor.is_playing_seeds is False
