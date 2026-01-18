import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from app.livekit.conductor import Conductor, ConductorState
from app.livekit.protocol import MsgType, AgentPacket

@pytest.fixture
def mock_room():
    room = MagicMock()
    room.local_participant.publish_data = AsyncMock()
    return room

@pytest.fixture
def mock_writer():
    return AsyncMock()

@pytest.fixture
def mock_metrics():
    return AsyncMock()

@pytest.fixture
def mock_resolver():
    resolver = AsyncMock()
    resolver.get_transcript_view.return_value.utterances = []
    return resolver

@pytest.fixture
def conductor(mock_room, mock_writer, mock_metrics, mock_resolver):
    # Patch LLMService class
    with patch("app.livekit.conductor.LLMService") as MockLLMClass:
        mock_instance = MockLLMClass.return_value
        # Default behavior: Alice speaks
        mock_instance.decide_speaker = AsyncMock(return_value={"speaker_id": "alice", "reason": "test"})
        mock_instance.generate_turn_text = AsyncMock(return_value="Hello")
        
        c = Conductor(mock_writer, mock_metrics, mock_resolver)
        c.room = mock_room
        c.session_id = "s1"
        c.branch_id = "b1"
        yield c

@pytest.mark.asyncio
async def test_finish_packet_handling(conductor):
    """Test that receiving a FINISH packet transitions state to ENDING."""
    conductor.state = ConductorState.LIVE
    
    # Simulate receiving FINISH packet
    packet = AgentPacket(
        type=MsgType.FINISH,
        session_id="s1"
    )
    
    # Manually invoke handler
    conductor._handle_packet(packet, "facilitator")
    
    # Wait for async transition task
    await asyncio.sleep(0.1)
    
    assert conductor.state == ConductorState.ENDING

@pytest.mark.asyncio
async def test_objective_check_trigger(conductor):
    """Test that _check_objectives returns True on trigger phrase."""
    # Test positive case
    history = ["Alice: Hello", "User: Let's wrap up this session"]
    assert await conductor._check_objectives(history) is True
    
    # Test negative case
    history = ["Alice: Hello", "User: Keep going"]
    assert await conductor._check_objectives(history) is False
