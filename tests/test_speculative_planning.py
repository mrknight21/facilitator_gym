import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.livekit.conductor import Conductor, ConductorState
from app.livekit.speculative import SpecPlan
from app.livekit.protocol import MsgType, AgentPacket

@pytest.mark.asyncio
async def test_speculative_planning_flow():
    # Mock dependencies
    mock_writer = MagicMock()
    mock_metrics = MagicMock()
    mock_resolver = MagicMock()
    mock_resolver.get_transcript_view = AsyncMock()
    mock_resolver.get_transcript_view.return_value.utterances = []
    
    # Mock LLM
    mock_llm = AsyncMock()
    mock_llm.plan_next_turn.return_value = {"speaker_id": "bob", "text": "Hello", "reason": "test"}
    
    # Patch LLMService in Conductor
    with patch("app.livekit.conductor.LLMService", return_value=mock_llm):
        conductor = Conductor(mock_writer, mock_metrics, mock_resolver)
        conductor.session_id = "test_session"
        conductor.branch_id = "test_branch"
        
        # Mock Room
        conductor.room = MagicMock()
        conductor.room.local_participant.publish_data = AsyncMock()
        
        # Start LIVE loop (mocked)
        conductor.state = ConductorState.LIVE
        conductor.history_cache = ["alice: Hi"]
        
        # 1. Simulate sending a turn (which spawns spec planner)
        conductor.current_turn_id = "turn-1"
        conductor.state_version = 1
        
        # Manually spawn spec planner as if send_speak_cmd did it
        spec_history = ["alice: Hi", "alice: How are you?"]
        conductor.spec_plan_task = asyncio.create_task(conductor._run_spec_planner(
            spec_history, {}, ["alice", "bob"], 1, "turn-1"
        ))
        
        # Wait for planner to finish
        await asyncio.sleep(0.1)
        
        assert conductor.spec_plan is not None
        assert conductor.spec_plan.speaker_id == "bob"
        assert conductor.spec_plan.after_turn_id == "turn-1"
        
        # 2. Simulate PLAYBACK_DONE matching the turn
        packet = AgentPacket(
            type=MsgType.PLAYBACK_DONE,
            session_id="test_session",
            turn_id="turn-1",
            payload={"speaker_id": "alice", "duration_ms": 1000}
        )
        
        # We can't easily run the full loop, but we can verify the logic condition
        # Check if spec plan is valid
        is_valid = (conductor.spec_plan and 
                    conductor.spec_plan.after_turn_id == "turn-1" and 
                    conductor.spec_plan.plan_version == conductor.state_version and
                    not conductor.is_processing_intervention)
        
        assert is_valid
        
        # 3. Simulate Intervention (Invalidation)
        await conductor._process_intervention("fac")
        
        assert conductor.spec_plan is None
        assert conductor.state_version == 2
        
        # Check validity again (should be false)
        is_valid_after = (conductor.spec_plan and 
                          conductor.spec_plan.after_turn_id == "turn-1")
        assert not is_valid_after
