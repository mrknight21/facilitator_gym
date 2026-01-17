import pytest
from app.api.intervene import intervene
from app.domain.schemas import InterveneReq

class MockVC:
    async def fork_branch(self, session_id, parent_branch_id, from_utterance_id, from_checkpoint_id, created_by):
        class Res:
            branch_id = "new_br"
        return Res()
    async def set_active_branch(self, session_id, branch_id):
        pass

class MockWriter:
    async def append_utterance_and_checkpoint(self, **kwargs):
        return {"utterance_id": "u_int", "checkpoint_id": "cp_int"}

class MockCP:
    pass

@pytest.mark.asyncio
async def test_intervene_api():
    vc = MockVC()
    writer = MockWriter()
    cp = MockCP()
    
    req = InterveneReq(
        parent_branch_id="b1",
        at_utterance_id="u1",
        created_by="user",
        intervention_text="stop"
    )
    
    res = await intervene("s1", req, vc, writer, cp)
    
    assert res.new_branch_id == "new_br"
    assert res.intervention_utterance_id == "u_int"
