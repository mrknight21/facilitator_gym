import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client(mock_db):
    # Mock LiveKit
    with pytest.MonkeyPatch.context() as m:
        # Patch dependencies in app.api.sessions since they are imported at top level
        m.setattr("app.api.sessions.create_token", lambda *args, **kwargs: "mock_token")
        m.setattr("app.api.sessions.VideoGrants", lambda **kwargs: MagicMock())
        m.setattr("app.api.sessions.Conductor", MagicMock())
        m.setattr("app.api.sessions.AgentWorker", MagicMock())
        
        # Also patch in tokens module just in case
        m.setattr("app.livekit.tokens.create_token", lambda *args, **kwargs: "mock_token")
        m.setattr("app.livekit.tokens.mint_token", lambda *args, **kwargs: "mock_token")
        
        # Mock Conductor instance methods
        mock_conductor_instance = AsyncMock()
        m.setattr("app.api.sessions.Conductor", lambda *args: mock_conductor_instance)
        
        # Mock AgentWorker instance methods
        mock_agent_instance = AsyncMock()
        m.setattr("app.api.sessions.AgentWorker", lambda *args: mock_agent_instance)
        
        # Break infinite loop in spawn_simulation
        async def mock_sleep(*args):
            raise asyncio.CancelledError()
            
        from app.api import sessions
        m.setattr(sessions.asyncio, "sleep", mock_sleep)
        
        with TestClient(app) as c:
            yield c

def test_e2e_flow(client):
    # 1. Create Case Study
    cs_payload = {
        "case_study_id": "cs_e2e",
        "title": "E2E Case",
        "seed_utterances": [
            {"seed_idx": 1, "speaker": "alice", "text": "Hello"}
        ]
    }
    resp = client.post("/case-studies", json=cs_payload)
    assert resp.status_code == 200

    # 2. Start Session
    start_payload = {
        "case_study_id": "cs_e2e",
        "created_by": "tester",
        "config": {"participants": ["alice"]}
    }
    resp = client.post("/sessions/start", json=start_payload)
    assert resp.status_code == 200
    sess_data = resp.json()
    session_id = sess_data["session_id"]
    root_branch_id = sess_data["root_branch_id"]

    # 3. Verify Transcript
    resp = client.get(f"/sessions/{session_id}/branches/{root_branch_id}/transcript")
    assert resp.status_code == 200
    transcript = resp.json()
    assert len(transcript["utterances"]) == 1
    assert transcript["utterances"][0]["text"] == "Hello"

    # 4. Intervene
    u1_id = transcript["utterances"][0]["utterance_id"]
    
    intervene_payload = {
        "parent_branch_id": root_branch_id,
        "at_utterance_id": u1_id,
        "created_by": "tester",
        "intervention_text": "Stop"
    }
    resp = client.post(f"/sessions/{session_id}/intervene", json=intervene_payload)
    assert resp.status_code == 200
    int_data = resp.json()
    new_branch_id = int_data["new_branch_id"]
    
    # 5. Verify New Branch Transcript
    resp = client.get(f"/sessions/{session_id}/branches/{new_branch_id}/transcript")
    assert resp.status_code == 200
    transcript_new = resp.json()
    # Should have seed + intervention
    assert len(transcript_new["utterances"]) == 2
    assert transcript_new["utterances"][1]["text"] == "Stop"
    
    # 6. Verify Tree
    resp = client.get(f"/sessions/{session_id}/branches")
    assert resp.status_code == 200
    branches = resp.json()
    assert len(branches) == 2
