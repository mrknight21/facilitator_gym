import pytest
import asyncio
import sys
import os
sys.path.append(os.getcwd())
from unittest.mock import AsyncMock, MagicMock, patch
from app.livekit.conductor import Conductor, ConductorState
from app.livekit.protocol import MsgType, AgentPacket

@pytest.mark.asyncio
async def test_conductor_rewind_flow():
    # Mocks
    mock_writer = AsyncMock()
    mock_metrics = MagicMock()
    mock_resolver = MagicMock()
    mock_rewind = AsyncMock()
    
    # Setup Conductor
    conductor = Conductor(mock_writer, mock_metrics, mock_resolver, mock_rewind)
    conductor.room = MagicMock()
    conductor.room.local_participant.publish_data = AsyncMock()
    conductor.session_id = "s1"
    conductor.branch_id = "b1"
    
    # 1. Test TIME_STOP
    packet = AgentPacket(type=MsgType.TIME_STOP, session_id="s1")
    conductor._handle_packet(packet, "fac")
    
    # Wait for async task
    await asyncio.sleep(0.1)
    assert conductor.state == ConductorState.PAUSED
    
    # 2. Test REWIND_TO
    # Mock Rewind Plan
    mock_plan = MagicMock()
    mock_plan.new_branch_id = "b2"
    mock_plan.replay_utterances = [
        MagicMock(speaker_id="ai", text="Hello", audio=MagicMock(url="audio.wav"))
    ]
    mock_plan.handoff_reason = "END_OF_TIMELINE"
    mock_rewind.create_rewind_plan.return_value = mock_plan
    
    packet = AgentPacket(
        type=MsgType.REWIND_TO, 
        session_id="s1", 
        payload={"target_utterance_id": "u1"}
    )
    conductor._handle_packet(packet, "fac")
    
    await asyncio.sleep(0.1)
    
    # Verify State
    assert conductor.state == ConductorState.REPLAYING
    assert conductor.branch_id == "b2"
    
    # Verify Replay Loop Started
    # We can't easily check if the loop is running without mocking _run_replay_loop or checking side effects.
    # Let's check if send_play_asset_cmd was called.
    # The loop runs in a task, so we need to give it time.
    await asyncio.sleep(0.1)
    
    # Verify PLAY_ASSET_CMD sent
    conductor.room.local_participant.publish_data.assert_called()
    call_args = conductor.room.local_participant.publish_data.call_args
    assert b"play_asset_cmd" in call_args[0][0]
    
    # 3. Test Playback Done -> Next Item or Finish
    # Since we only have 1 item, it should wait for done.
    # We need to simulate PLAYBACK_DONE
    conductor.playback_done_event.set()
    
    await asyncio.sleep(0.6)
    
    # Should transition to LIVE after loop finishes
    assert conductor.state == ConductorState.LIVE
