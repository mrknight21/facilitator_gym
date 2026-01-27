import pytest
import sys
import os
sys.path.append(os.getcwd())
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.domain.schemas import RewindToReq



@pytest.mark.asyncio
async def test_rewind_plan_integration(mock_db):
    # 1. Setup Data
    # Session
    await mock_db["sessions"].insert_one({
        "_id": "session_1",
        "case_study_id": "cs1",
        "created_by": "tester",
        "active_branch_id": "branch_1"
    })
    
    # Branch 1
    await mock_db["branches"].insert_one({
        "_id": "branch_1",
        "session_id": "session_1",
        "branch_label": "main",
        "created_at": "2023-01-01T00:00:00Z"
    })
    
    # Utterances
    # u1: AI (Target)
    # u2: AI (Replay)
    # u3: User Intervention (Handoff)
    await mock_db["utterances"].insert_many([
        {
            "_id": "u1",
            "session_id": "session_1",
            "branch_id": "branch_1",
            "seq_in_branch": 1,
            "kind": "ai",
            "text": "Hello, I am the AI.",
            "speaker_id": "ai"
        },
        {
            "_id": "u2",
            "session_id": "session_1",
            "branch_id": "branch_1",
            "seq_in_branch": 2,
            "kind": "ai",
            "text": "How can I help you?",
            "speaker_id": "ai"
        },
        {
            "_id": "u3",
            "session_id": "session_1",
            "branch_id": "branch_1",
            "seq_in_branch": 3,
            "kind": "user_intervention",
            "text": "Wait, stop.",
            "speaker_id": "facilitator"
        }
    ])
    
    # Checkpoint for u1 (Target)
    await mock_db["checkpoints"].insert_one({
        "_id": "cp1",
        "session_id": "session_1",
        "branch_id": "branch_1",
        "at_utterance_id": "u1",
        "created_at": "2023-01-01T00:00:01Z",
        "state": {}
    })
    
    # 2. Call API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        req = RewindToReq(
            branch_id="branch_1",
            target_utterance_id="u1",
            created_by="tester"
        )
        
        resp = await ac.post("/sessions/session_1/rewind/plan", json=req.model_dump())
        
        assert resp.status_code == 200
        data = resp.json()
        
        # 3. Verify Response
        assert data["target_utterance_id"] == "u1"
        assert data["fork_checkpoint_id"] == "cp1"
        assert data["handoff_reason"] == "HIT_FACILITATOR_TURN"
        assert data["handoff_at_utterance_id"] == "u3"
        
        # Replay utterances should be [u2]
        # u1 is target (exclusive start)
        # u3 is facilitator (exclusive end)
        assert len(data["replay_utterances"]) == 1
        assert data["replay_utterances"][0]["utterance_id"] == "u2"
        
        new_branch_id = data["new_branch_id"]
        assert new_branch_id != "branch_1"
        
        # 4. Verify Side Effects
        # New branch created
        new_branch = await mock_db["branches"].find_one({"_id": new_branch_id})
        assert new_branch is not None
        assert new_branch["parent_branch_id"] == "branch_1"
        assert new_branch["fork_from_utterance_id"] == "u1"
        
        # Session active branch updated
        session = await mock_db["sessions"].find_one({"_id": "session_1"})
        assert session["active_branch_id"] == new_branch_id
