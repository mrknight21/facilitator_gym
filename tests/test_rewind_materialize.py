import pytest
from unittest.mock import MagicMock, AsyncMock
from app.domain.services.materialize_timeline import MaterializeTimelineService


@pytest.mark.asyncio
async def test_materialize_timeline_with_replay():
    """
    Test: Rewind at turn 10 -> target 4 -> replay turns 5-7 -> handoff at 8
    """
    # Setup Mocks
    branch_repo = AsyncMock()
    utterance_repo = AsyncMock()
    replay_event_repo = AsyncMock()
    resolver = AsyncMock()
    
    # Mock Branch (Forked)
    branch_repo.get.return_value = {
        "_id": "branch-2",
        "parent_id": "branch-1",
        "forked_at_utterance_id": "utt-4"
    }
    
    # Mock Replay Event
    replay_event_repo.list_by_branch.return_value = [{
        "replay_event_id": "evt-1",
        "from_branch_id": "branch-1",
        "to_branch_id": "branch-2",
        "target_turn_id": "utt-4",
        "replayed_turn_ids": ["utt-5", "utt-6", "utt-7"],
        "handoff_at_turn_id": "utt-8",
        "handoff_reason": "HIT_FACILITATOR_TURN",
        "status": "completed"
    }]
    
    # Mock Parent Branch Transcript (Turns 1-4)
    parent_view = MagicMock()
    parent_view.utterances = [
        MagicMock(utterance_id="utt-1", speaker_id="alice", text="Turn 1", audio=None),
        MagicMock(utterance_id="utt-2", speaker_id="bob", text="Turn 2", audio=None),
        MagicMock(utterance_id="utt-3", speaker_id="alice", text="Turn 3", audio=None),
        MagicMock(utterance_id="utt-4", speaker_id="bob", text="Turn 4", audio=None),
    ]
    resolver.get_transcript_view.return_value = parent_view
    
    # Mock Replayed Utterances (5-7)
    async def mock_find_one(query):
        utt_id = query.get("_id")
        return {
            "_id": utt_id,
            "speaker_id": "alice" if utt_id in ["utt-5", "utt-7"] else "bob",
            "text": f"Replayed {utt_id}",
            "audio": {}
        }
    utterance_repo.col.find_one = mock_find_one
    
    # Mock New Turns (after divergence)
    utterance_repo.get_by_branch.return_value = [
        {"_id": "utt-new-1", "speaker_id": "facilitator", "text": "New Turn 1", "audio": {}}
    ]
    
    # Execute
    service = MaterializeTimelineService(branch_repo, utterance_repo, replay_event_repo, resolver)
    result = await service.get_materialized_timeline("sess-1", "branch-2")
    
    # Assert
    assert len(result) == 8  # 4 original + 3 replayed + 1 new
    
    # Check sources
    assert result[0]["source"] == "original"
    assert result[3]["source"] == "original"
    assert result[4]["source"] == "replayed"
    assert result[5]["source"] == "replayed"
    assert result[6]["source"] == "replayed"
    assert result[7]["source"] == "new"
    
    # Check replay_event_id
    assert result[4]["replay_event_id"] == "evt-1"
    assert result[7]["replay_event_id"] is None


@pytest.mark.asyncio
async def test_materialize_timeline_no_fork():
    """
    Test: Non-forked branch returns all turns as "original".
    """
    branch_repo = AsyncMock()
    utterance_repo = AsyncMock()
    replay_event_repo = AsyncMock()
    resolver = AsyncMock()
    
    # Mock Non-Forked Branch
    branch_repo.get.return_value = {
        "_id": "branch-1",
        "parent_id": None,
        "forked_at_utterance_id": None
    }
    
    # Mock Utterances
    utterance_repo.get_by_branch.return_value = [
        {"_id": "utt-1", "speaker_id": "alice", "text": "Turn 1", "audio": {}},
        {"_id": "utt-2", "speaker_id": "bob", "text": "Turn 2", "audio": {}},
    ]
    
    service = MaterializeTimelineService(branch_repo, utterance_repo, replay_event_repo, resolver)
    result = await service.get_materialized_timeline("sess-1", "branch-1")
    
    assert len(result) == 2
    assert all(item["source"] == "original" for item in result)
