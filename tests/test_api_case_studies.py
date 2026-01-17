import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.case_studies import get_repo
from app.domain.schemas import CaseStudyCreate, CaseStudyOut

# Mock repo dependency
class MockCaseStudyRepo:
    def __init__(self):
        self.store = {}

    async def create(self, cs: CaseStudyCreate) -> CaseStudyOut:
        doc = cs.model_dump()
        doc["_id"] = doc["case_study_id"]
        self.store[doc["case_study_id"]] = doc
        return CaseStudyOut(**doc)

    async def get(self, case_study_id: str) -> CaseStudyOut | None:
        doc = self.store.get(case_study_id)
        if doc:
            return CaseStudyOut(**doc)
        return None

    async def list_all(self) -> list[CaseStudyOut]:
        return [CaseStudyOut(**doc) for doc in self.store.values()]

@pytest.fixture
def client():
    # Override dependency
    mock_repo = MockCaseStudyRepo()
    app.dependency_overrides[get_repo] = lambda: mock_repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_create_and_get_case_study(client):
    payload = {
        "case_study_id": "case_abc",
        "title": "Test Case",
        "description": "A test description",
        "participants": ["Alice", "Bob"],
        "seed_utterances": [
            {"seed_idx": 1, "speaker": "S1", "text": "Hello"}
        ]
    }
    # Create
    resp = client.post("/case-studies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_study_id"] == "case_abc"
    assert data["description"] == "A test description"
    assert data["participants"] == ["Alice", "Bob"]
    assert len(data["seed_utterances"]) == 1

    # Get
    resp = client.get("/case-studies/case_abc")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test Case"

    # Duplicate create
    resp = client.post("/case-studies", json=payload)
    assert resp.status_code == 400

def test_list_case_studies(client):
    # 1. Create two case studies
    c1 = {
        "case_study_id": "cs_1",
        "title": "Case 1",
        "seed_utterances": []
    }
    c2 = {
        "case_study_id": "cs_2",
        "title": "Case 2",
        "seed_utterances": []
    }
    client.post("/case-studies", json=c1)
    client.post("/case-studies", json=c2)

    # 2. List
    resp = client.get("/case-studies")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    ids = [d["case_study_id"] for d in data]
    assert "cs_1" in ids
    assert "cs_2" in ids
