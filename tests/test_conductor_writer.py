import pytest
from app.domain.services.conductor_writer import ConductorWriter
from app.domain.schemas import UtteranceView, Timing

class MockRepo:
    def __init__(self):
        self.store = {}
        self.col = self # Mock col.find_one/update_one
    async def create(self, doc):
        self.store[doc["_id"]] = doc
        return doc
    async def get(self, id):
        return self.store.get(id)
    async def find_one(self, query):
        if "event_id" in query:
            for d in self.store.values():
                if d.get("event_id") == query["event_id"]:
                    return d
        return None
    async def update_one(self, query, update):
        # Mock update
        return None
    async def get_by_branch(self, session_id, branch_id):
        return [d for d in self.store.values() if d["session_id"] == session_id and d["branch_id"] == branch_id]
    async def get_by_utterance(self, session_id, branch_id, utterance_id):
        # For checkpoint repo
        for d in self.store.values():
            if d.get("at_utterance_id") == utterance_id:
                return d
        return None

class MockSessionRepo(MockRepo):
    pass
class MockBranchRepo(MockRepo):
    pass
class MockUtteranceRepo(MockRepo):
    pass
class MockCheckpointRepo(MockRepo):
    pass

class MockResolver:
    async def get_transcript_view(self, session_id, branch_id):
        class View:
            utterances = []
        return View()

@pytest.mark.asyncio
async def test_conductor_writer_append():
    sess_repo = MockSessionRepo()
    br_repo = MockBranchRepo()
    utt_repo = MockUtteranceRepo()
    cp_repo = MockCheckpointRepo()
    resolver = MockResolver()
    
    writer = ConductorWriter(sess_repo, br_repo, utt_repo, cp_repo, resolver)
    
    # Setup
    await sess_repo.create({"_id": "s1", "write_version": 0})
    await br_repo.create({"_id": "b1", "session_id": "s1"})
    
    # Append
    res = await writer.append_utterance_and_checkpoint(
        "s1", "b1", "ai", "alice", "hello", {}, {}, "evt1"
    )
    
    assert res["utterance_id"] in utt_repo.store
    assert res["checkpoint_id"] in cp_repo.store
    
    # Idempotency
    res2 = await writer.append_utterance_and_checkpoint(
        "s1", "b1", "ai", "alice", "hello", {}, {}, "evt1"
    )
    assert res2["utterance_id"] == res["utterance_id"]
