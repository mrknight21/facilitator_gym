import pytest
from app.domain.services.version_control import VersionControl
from app.domain.schemas import ForkRes

class MockRepo:
    def __init__(self):
        self.store = {}
    async def create(self, doc):
        self.store[doc["_id"]] = doc
        return doc
    async def get(self, id):
        return self.store.get(id)
    async def update(self, id, update):
        if id in self.store:
            # Simple $set handling
            if "$set" in update:
                self.store[id].update(update["$set"])
            else:
                self.store[id].update(update)
    async def list_by_session(self, session_id):
        return [d for d in self.store.values() if d["session_id"] == session_id]

class MockBranchRepo(MockRepo):
    pass

class MockSessionRepo(MockRepo):
    pass

@pytest.mark.asyncio
async def test_fork_branch():
    br_repo = MockBranchRepo()
    sess_repo = MockSessionRepo()
    vc = VersionControl(br_repo, sess_repo)

    # Setup
    await br_repo.create({"_id": "main", "session_id": "s1", "branch_label": "main"})
    await sess_repo.create({"_id": "s1", "active_branch_id": "main"})

    # Fork
    res = await vc.fork_branch("s1", "main", "utt_1", None, "user_1")
    
    assert res.parent_branch_id == "main"
    assert res.fork_from_utterance_id == "utt_1"
    assert res.branch_id in br_repo.store
    
    # Verify list
    branches = await vc.list_branches("s1")
    assert len(branches) == 2

    # Set active
    await vc.set_active_branch("s1", res.branch_id)
    sess = await sess_repo.get("s1")
    assert sess["active_branch_id"] == res.branch_id
