import pytest
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.livekit.conductor import Conductor, ConductorState
from app.livekit.protocol import MsgType, SpeakCmdPayload, AgentPacket
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
                utterance_id="u1", speaker_id="alice", kind="seed", text="seed1", display_id="1",
                timing=Timing(t_start_ms=0, t_end_ms=50) # Fast
            ),
            UtteranceView(
                utterance_id="u2", speaker_id="bob", kind="seed", text="seed2", display_id="2",
                timing=Timing(t_start_ms=50, t_end_ms=100) # Fast
            )
        ]
    resolver.get_transcript_view.return_value = View()
    return resolver

@pytest.fixture
def conductor(mock_room, mock_writer, mock_metrics, mock_resolver):
    # Patch the class itself where it is imported in conductor logic
    # Since we moved import to top level: 'app.livekit.conductor.LLMService'
    with patch("app.livekit.conductor.LLMService") as MockLLMClass:
        # Mock instance
        mock_instance = MockLLMClass.return_value
        mock_instance.decide_speaker = AsyncMock(return_value={"speaker_id": "alice", "reason": "test"})
        mock_instance.generate_turn_text = AsyncMock(return_value="Hello world")
        
        c = Conductor(mock_writer, mock_metrics, mock_resolver)
        c.room = mock_room
        c.session_id = "s1"
        c.branch_id = "b1"
        yield c

@pytest.mark.asyncio
async def test_seed_playback_transition(conductor, mock_resolver, mock_room):
    # Start in INIT
    assert conductor.state == ConductorState.INIT
    
    # Transition to PLAYING_SEED
    await conductor.transition_to(ConductorState.PLAYING_SEED)
    assert conductor.state == ConductorState.PLAYING_SEED
    assert conductor.seed_task is not None
    
    # Wait for completion (seeds are 50ms each + 0.5s pause)
    # We might need to mock sleep to speed up?
    # For now, let's just wait a bit longer than real time
    await asyncio.sleep(2.0)
    
    # Validation
    assert conductor.state == ConductorState.LIVE
    mock_resolver.get_transcript_view.assert_called()
    
    # Check that SPEAK commands were sent regarding seeds
    calls = mock_room.local_participant.publish_data.call_args_list
    assert len(calls) >= 2 # At least 2 seeds
    
    # Verify first seed packet
    args, kwargs = calls[0]
    payload = json.loads(args[0].decode("utf-8"))
    assert payload["type"] == MsgType.SPEAK_CMD
    inner = payload["payload"]
    assert inner["text"] == "seed1"
    assert inner["speaker_id"] == "alice"

@pytest.mark.asyncio
async def test_intervention_during_seed(conductor, mock_resolver):
    # Start seed
    await conductor.transition_to(ConductorState.PLAYING_SEED)
    
    # Simulate FAC_START intervention
    packet = AgentPacket(type=MsgType.FAC_START, session_id="s1")
    msg_bytes = packet.model_dump_json().encode("utf-8")
    
    conductor.on_data_received(msg_bytes, MagicMock(identity="user"), None)
    
    # Give it a moment to process async task
    await asyncio.sleep(0.1)
    
    # It should cancel seed and go to LIVE
    assert conductor.state == ConductorState.LIVE
    
    # Should have sent stop command
    # (Since current_speaker might have been set)
