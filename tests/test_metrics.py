import pytest
from app.metrics.engine import MetricsEngine
from app.domain.schemas import UtteranceView, Timing

class MockRepo:
    def __init__(self):
        self.store = {}
    async def create(self, doc):
        self.store[doc["_id"]] = doc
        return doc

class MockMetricsRepo(MockRepo):
    pass

class MockCheckpointRepo(MockRepo):
    def __init__(self):
        super().__init__()
        self.col = self # Mock col.find_one
    async def find_one(self, query):
        return self.store.get(query["_id"])

class MockResolver:
    async def get_transcript_view(self, session_id, branch_id):
        class View:
            utterances = [
                UtteranceView(
                    utterance_id="u1", speaker_id="alice", kind="ai", text="hi", display_id="1",
                    timing=Timing(t_start_ms=1000, t_end_ms=2000)
                ),
                UtteranceView(
                    utterance_id="u2", speaker_id="bob", kind="ai", text="ho", display_id="2",
                    timing=Timing(t_start_ms=2000, t_end_ms=5000)
                )
            ]
        return View()

@pytest.mark.asyncio
async def test_metrics_engine():
    m_repo = MockMetricsRepo()
    cp_repo = MockCheckpointRepo()
    resolver = MockResolver()
    engine = MetricsEngine(m_repo, resolver, cp_repo)

    # Setup checkpoint
    cp_repo.store["cp1"] = {"_id": "cp1", "at_utterance_id": "u2"}

    # Compute
    metrics = await engine.compute_for_checkpoint("s1", "b1", "cp1")
    
    assert metrics["speaking_time_ms"]["alice"] == 1000
    assert metrics["speaking_time_ms"]["bob"] == 3000
    
    # Verify stored
    assert len(m_repo.store) == 1
