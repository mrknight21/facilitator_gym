import pytest
from app.domain.services.checkpointing import Checkpointing

class MockRepo:
    def __init__(self):
        self.store = {}
    async def create(self, doc):
        self.store[doc["_id"]] = doc
        return doc
    async def list_by_branch(self, session_id, branch_id):
        return [d for d in self.store.values() if d["session_id"] == session_id and d["branch_id"] == branch_id]

class MockCheckpointRepo(MockRepo):
    pass

@pytest.mark.asyncio
async def test_create_and_list_checkpoints():
    repo = MockCheckpointRepo()
    cp = Checkpointing(repo)

    # Create
    cp_id = await cp.create_checkpoint("s1", "b1", "u1", {"floor": "empty"})
    assert cp_id in repo.store
    
    # List
    checkpoints = await cp.list_checkpoints("s1", "b1")
    assert len(checkpoints) == 1
    assert checkpoints[0].checkpoint_id == cp_id
    assert checkpoints[0].state["floor"] == "empty"
