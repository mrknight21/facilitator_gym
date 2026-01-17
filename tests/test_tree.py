import pytest
from app.domain.services.version_control import VersionControl
from app.domain.schemas import BranchOut

class MockRepo:
    def __init__(self):
        self.store = {}
    async def list_by_session(self, session_id):
        return [d for d in self.store.values() if d["session_id"] == session_id]

class MockBranchRepo(MockRepo):
    pass
class MockSessionRepo(MockRepo):
    pass

@pytest.mark.asyncio
async def test_tree_reconstruction():
    br_repo = MockBranchRepo()
    sess_repo = MockSessionRepo()
    vc = VersionControl(br_repo, sess_repo)
    
    # Setup tree
    # root
    #  |- b1 (from u1)
    #      |- b2 (from u2)
    br_repo.store["root"] = {"_id": "root", "session_id": "s1", "branch_label": "main", "created_at": "100"}
    br_repo.store["b1"] = {"_id": "b1", "session_id": "s1", "parent_branch_id": "root", "fork_from_utterance_id": "u1", "branch_label": "b1", "created_at": "200"}
    br_repo.store["b2"] = {"_id": "b2", "session_id": "s1", "parent_branch_id": "b1", "fork_from_utterance_id": "u2", "branch_label": "b2", "created_at": "300"}
    
    branches = await vc.list_branches("s1")
    
    assert len(branches) == 3
    
    # Verify we can build a tree
    node_map = {b.branch_id: b for b in branches}
    children = {b.branch_id: [] for b in branches}
    
    for b in branches:
        if b.parent_branch_id:
            children[b.parent_branch_id].append(b.branch_id)
            
    assert "b1" in children["root"]
    assert "b2" in children["b1"]
    assert node_map["b1"].created_at == "200"
