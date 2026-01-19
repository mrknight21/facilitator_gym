import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.livekit.conductor import Conductor, ConductorState
from app.livekit.protocol import MsgType, AgentPacket

@pytest.mark.asyncio
async def test_fac_ack_sent_on_fac_start():
    # Setup
    conductor_writer = MagicMock()
    metrics_engine = MagicMock()
    transcript_resolver = MagicMock()
    conductor = Conductor(conductor_writer, metrics_engine, transcript_resolver)
    
    # Mock Room and Local Participant
    conductor.room = MagicMock()
    conductor.room.local_participant = MagicMock()
    conductor.room.local_participant.publish_data = AsyncMock()
    conductor.session_id = "test_session" # Fix Pydantic error
    
    # Simulate receiving FAC_START
    packet = AgentPacket(
        type=MsgType.FAC_START,
        session_id="test_session",
        payload={}
    )
    sender_id = "test_user"
    
    # Act
    # _handle_packet is sync
    conductor._handle_packet(packet, sender_id)
    
    # Wait for async tasks to run
    await asyncio.sleep(0.1)
    
    # Assert
    # 1. State changed
    assert conductor.is_recording_facilitator is True
    
    # 2. ACK sent
    conductor.room.local_participant.publish_data.assert_called()
    call_args = conductor.room.local_participant.publish_data.call_args
    assert call_args is not None
    
    data_sent, kwargs = call_args
    payload_json = data_sent[0].decode("utf-8")
    
    assert "fac_ack" in payload_json
    assert "test_user" in payload_json
    assert kwargs['reliable'] is True
    assert kwargs['destination_identities'] == ["test_user"]
