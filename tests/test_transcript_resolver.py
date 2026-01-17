import pytest
from app.domain.services.transcript_resolver import TranscriptResolver

class MockRepo:
    def __init__(self):
        self.store = {}
    async def get(self, id):
        return self.store.get(id)
    async def get_by_branch(self, session_id, branch_id):
        # Return sorted by seq_in_branch
        utts = [u for u in self.store.values() if u["branch_id"] == branch_id]
        return sorted(utts, key=lambda x: x.get("seq_in_branch", 0))

class MockBranchRepo(MockRepo):
    pass

class MockUtteranceRepo(MockRepo):
    pass

@pytest.mark.asyncio
async def test_transcript_resolver():
    br_repo = MockBranchRepo()
    utt_repo = MockUtteranceRepo()
    resolver = TranscriptResolver(br_repo, utt_repo)

    # Setup branches
    # Root
    br_repo.store["root"] = {"_id": "root", "parent_branch_id": None}
    # Fork 1 from root at utt_2
    br_repo.store["br1"] = {"_id": "br1", "parent_branch_id": "root", "fork_from_utterance_id": "utt_2"}
    # Fork 2 from br1 at utt_2_1
    br_repo.store["br2"] = {"_id": "br2", "parent_branch_id": "br1", "fork_from_utterance_id": "utt_2_1"}

    # Setup utterances
    # Root: 1, 2, 3 (3 is ignored by br1)
    utt_repo.store["utt_1"] = {"_id": "utt_1", "branch_id": "root", "kind": "seed", "seed_idx": 1, "seq_in_branch": 1}
    utt_repo.store["utt_2"] = {"_id": "utt_2", "branch_id": "root", "kind": "seed", "seed_idx": 2, "seq_in_branch": 2}
    utt_repo.store["utt_3"] = {"_id": "utt_3", "branch_id": "root", "kind": "seed", "seed_idx": 3, "seq_in_branch": 3}
    
    # br1: 2.1, 2.2 (2.2 ignored by br2)
    utt_repo.store["utt_2_1"] = {"_id": "utt_2_1", "branch_id": "br1", "kind": "ai", "seq_in_branch": 1}
    utt_repo.store["utt_2_2"] = {"_id": "utt_2_2", "branch_id": "br1", "kind": "ai", "seq_in_branch": 2}
    
    # br2: 2.1.1
    utt_repo.store["utt_2_1_1"] = {"_id": "utt_2_1_1", "branch_id": "br2", "kind": "ai", "seq_in_branch": 1}

    # Test view for br2
    view = await resolver.get_transcript_view("s1", "br2")
    
    ids = [u.display_id for u in view.utterances]
    # Expected: 1, 2, 2.1, 2.1.1
    assert ids == ["1", "2", "2.1", "2.1.1"]
    
    # Test view for br1
    view1 = await resolver.get_transcript_view("s1", "br1")
    ids1 = [u.display_id for u in view1.utterances]
    # Expected: 1, 2, 2.1, 2.2
    assert ids1 == ["1", "2", "2.1", "2.2"]
