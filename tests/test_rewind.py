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

class MockBranchRepo(MockRepo):
    pass

class MockUtteranceRepo(MockRepo):
    async def get_by_branch(self, session_id, branch_id):
        # Return list of utterances for this branch
        # For simplicity, return all utterances in store that match branch_id
        # In real repo, this is a query.
        res = []
        for u in self.store.values():
            if u.get("branch_id") == branch_id:
                res.append(u)
        # Sort by seq_in_branch
        res.sort(key=lambda x: x.get("seq_in_branch", 0))
        return res

@pytest.mark.asyncio
async def test_rewind_plan():
    sess_repo = MockSessionRepo()
    cp_repo = MockCheckpointRepo()
    utt_repo = MockUtteranceRepo()
    branch_repo = MockBranchRepo()
    vc = MockVC()
    
    # Setup
    await sess_repo.create({"_id": "s1"})
    await branch_repo.create({"_id": "b1", "session_id": "s1"})
    
    # Utterances: u1 (target), u2 (future), u3 (facilitator)
    await utt_repo.create({
        "_id": "u1", "branch_id": "b1", "seq_in_branch": 1, "kind": "ai", "text": "Hello"
    })
    await utt_repo.create({
        "_id": "u2", "branch_id": "b1", "seq_in_branch": 2, "kind": "ai", "text": "How are you?"
    })
    await utt_repo.create({
        "_id": "u3", "branch_id": "b1", "seq_in_branch": 3, "kind": "user_intervention", "text": "Stop"
    })
    
    # Checkpoint for u1
    await cp_repo.create({"_id": "cp1", "at_utterance_id": "u1"})
    
    # Req
    from app.api.rewind import rewind_plan
    from app.domain.schemas import RewindToReq
    
    req = RewindToReq(branch_id="b1", target_utterance_id="u1", created_by="user")
    
    res = await rewind_plan("s1", req, vc, cp_repo, utt_repo, branch_repo)
    
    assert res.new_branch_id == "new_br"
    assert res.target_utterance_id == "u1"
    
    # Replay utterances should contain u2 only
    # u1 is target (exclusive start)
    # u3 is facilitator (exclusive end)
    assert len(res.replay_utterances) == 1
    assert res.replay_utterances[0].utterance_id == "u2"
    
    assert res.handoff_reason == "HIT_FACILITATOR_TURN"
    assert res.handoff_at_utterance_id == "u3"
