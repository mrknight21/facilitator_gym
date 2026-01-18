import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.livekit.conductor import Conductor, ConductorState
from app.livekit.protocol import AgentPacket, MsgType

@pytest.mark.asyncio
async def test_conductor_ptt_flow():
    # Mocks
    writer = AsyncMock()
    metrics = MagicMock()
    resolver = MagicMock()
    
    # Mock STTService
    with patch("app.livekit.conductor.STTService") as MockSTT:
        stt_instance = MockSTT.return_value
        stt_instance.transcribe = AsyncMock(return_value="This is a test intervention.")
        
        conductor = Conductor(writer, metrics, resolver)
        conductor.room = MagicMock() # Mock LiveKit room
        
        # 1. Simulate FAC_START
        start_packet = AgentPacket(type=MsgType.FAC_START, session_id="test", payload={})
        conductor._handle_packet(start_packet, "facilitator_user")
        
        assert conductor.is_recording_facilitator == True
        assert conductor.is_processing_intervention == True
        
        # 2. Simulate Audio Data Frame
        # Direct buffer text
        conductor.audio_capture_buffer.extend(b'\x00' * 100) # 100 bytes of silence
        
        # 3. Simulate FAC_END
        end_packet = AgentPacket(type=MsgType.FAC_END, session_id="test", payload={})
        conductor._handle_packet(end_packet, "facilitator_user")
        
        # Wait for async processing
        assert conductor.is_recording_facilitator == False
        await asyncio.sleep(0.1) # Yield to event loop for _finalize_recording
        
        # 4. Assertions
        stt_instance.transcribe.assert_awaited_once()
        args, kwargs = stt_instance.transcribe.call_args
        assert len(args[0]) > 0 # Some WAV bytes
        
        writer.append_utterance_and_checkpoint.assert_awaited_once()
        call_args = writer.append_utterance_and_checkpoint.call_args
        assert call_args[0][4] == "This is a test intervention." # text
        assert call_args[0][3] == "facilitator_user" # identity
