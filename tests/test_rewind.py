import pytest
from app.api.rewind import rewind, continue_from_rewind
from app.domain.schemas import RewindReq, ContinueFromRewindReq

class MockRepo:
    def __init__(self):
        self.store = {}
        self.col = self
    async def create(self, doc):
        self.store[doc["_id"]] = doc
        return doc
    async def get(self, id):
        return self.store.get(id)
    async def update(self, id, update):
        if id in self.store:
            self.store[id].update(update)
    async def find_one(self, query):
        return self.store.get(query["_id"])

class MockSessionRepo(MockRepo):
    pass
class MockCheckpointRepo(MockRepo):
    pass

class MockVC:
    async def fork_branch(self, session_id, parent_branch_id, from_utterance_id, from_checkpoint_id, created_by):
        class Res:
            branch_id = "new_br"
        return Res()
    async def set_active_branch(self, session_id, branch_id):
        pass

@pytest.mark.asyncio
async def test_rewind_api():
    sess_repo = MockSessionRepo()
    cp_repo = MockCheckpointRepo()
    vc = MockVC()
    
    # Setup
    await sess_repo.create({"_id": "s1"})
    await cp_repo.create({"_id": "cp1", "at_utterance_id": "u1"})
    
    # Rewind
    req = RewindReq(branch_id="b1", checkpoint_id="cp1")
    await rewind("s1", req, sess_repo)
    
    s = await sess_repo.get("s1")
    assert s["playhead"]["checkpoint_id"] == "cp1"
    
    # Continue
    cont_req = ContinueFromRewindReq(created_by="user")
    res = await continue_from_rewind("s1", cont_req, vc, sess_repo, cp_repo)
    
    assert res.new_branch_id == "new_br"
    assert res.checkpoint_id == "cp1"
    
    s = await sess_repo.get("s1")
    assert s["playhead"] is None
