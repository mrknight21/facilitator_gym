import pytest
from app.domain.services.session_manager import SessionManager
from app.domain.schemas import SessionStartReq, SessionConfig, CaseStudyCreate, SeedUtteranceIn

class MockRepo:
    def __init__(self):
        self.store = {}
    async def create(self, doc):
        # Handle Pydantic models if passed (CaseStudyRepo.create takes model)
        if hasattr(doc, "model_dump"):
            d = doc.model_dump()
            d["_id"] = d.get("case_study_id")
            self.store[d["_id"]] = d
            return doc
        self.store[doc["_id"]] = doc
        return doc
    async def get(self, id):
        d = self.store.get(id)
        # CaseStudyRepo.get returns model
        if d and "seed_utterances" in d:
             # Reconstruct model for CaseStudy
             # But here we are mocking, so we can return object with attribute access if needed
             # The manager accesses .seed_utterances
             # Let's return a simple object wrapper
             class Obj:
                 def __init__(self, d):
                     self.__dict__.update(d)
                     # Convert seed_utterances to objects
                     self.seed_utterances = [type('Seed', (), s) for s in d['seed_utterances']]
             return Obj(d)
        return d

class MockCaseStudyRepo(MockRepo):
    pass

class MockSessionRepo(MockRepo):
    pass

class MockBranchRepo(MockRepo):
    pass

class MockUtteranceRepo(MockRepo):
    pass

@pytest.mark.asyncio
async def test_start_session():
    cs_repo = MockCaseStudyRepo()
    sess_repo = MockSessionRepo()
    br_repo = MockBranchRepo()
    utt_repo = MockUtteranceRepo()

    # Seed data
    cs = CaseStudyCreate(
        case_study_id="case_1",
        seed_utterances=[
            SeedUtteranceIn(seed_idx=1, speaker="A", text="Hi"),
            SeedUtteranceIn(seed_idx=2, speaker="B", text="Hello")
        ]
    )
    await cs_repo.create(cs)

    mgr = SessionManager(sess_repo, br_repo, utt_repo, cs_repo)

    req = SessionStartReq(
        case_study_id="case_1",
        created_by="user_1",
        config=SessionConfig(participants=["A", "B"])
    )

    res = await mgr.start_session(req)

    assert res.session_id in sess_repo.store
    assert res.root_branch_id in br_repo.store
    assert len(utt_repo.store) == 2
    
    # Check chain
    utts = sorted(utt_repo.store.values(), key=lambda x: x["seed_idx"])
    assert utts[0]["prev_utterance_id"] is None
    assert utts[1]["prev_utterance_id"] == utts[0]["_id"]
    assert utts[0]["text"] == "Hi"
    assert utts[1]["text"] == "Hello"
