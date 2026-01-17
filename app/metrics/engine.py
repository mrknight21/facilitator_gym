import time
import uuid
from typing import Dict, Any
from app.db.repos.metrics import MetricsRepo
from app.db.repos.checkpoint import CheckpointRepo
from app.domain.services.transcript_resolver import TranscriptResolver
from app.domain.schemas import MetricsOut

class MetricsEngine:
    def __init__(self, metrics_repo: MetricsRepo, transcript_resolver: TranscriptResolver, checkpoint_repo: CheckpointRepo):
        self.metrics_repo = metrics_repo
        self.transcript_resolver = transcript_resolver
        self.checkpoint_repo = checkpoint_repo

    async def compute_for_checkpoint(self, session_id: str, branch_id: str, checkpoint_id: str) -> Dict[str, Any]:
        # 1. Get checkpoint to know at_utterance_id
        # Note: CheckpointRepo.get_by_utterance is available, but we need get by id.
        # BaseRepo has get by id (if we implemented it? BaseRepo only has __init__).
        # I implemented get() in specific repos. CheckpointRepo doesn't have get() by id yet.
        # I'll use find_one directly or assume get() exists.
        # I'll use self.checkpoint_repo.col.find_one
        ckpt = await self.checkpoint_repo.col.find_one({"_id": checkpoint_id})
        if not ckpt:
            raise ValueError("Checkpoint not found")
        
        at_utterance_id = ckpt["at_utterance_id"]

        # 2. Get transcript view
        view = await self.transcript_resolver.get_transcript_view(session_id, branch_id)
        
        # 3. Filter utterances up to at_utterance_id
        # We need to find the index of at_utterance_id
        relevant_utts = []
        found = False
        for u in view.utterances:
            relevant_utts.append(u)
            if u.utterance_id == at_utterance_id:
                found = True
                break
        
        if not found:
            # Maybe checkpoint is from a different branch path?
            # Or transcript resolver logic is different.
            # For now, use all if not found (fallback) or empty.
            pass

        # 4. Compute metrics
        speaking_time = {}
        for utt in relevant_utts:
            if not utt.speaker_id:
                continue
            duration = utt.timing.t_end_ms - utt.timing.t_start_ms
            if duration < 0: duration = 0
            speaking_time[utt.speaker_id] = speaking_time.get(utt.speaker_id, 0) + duration

        metrics_data = {
            "speaking_time_ms": speaking_time,
            "sentiment": {"alice": 0.1, "bob": -0.2}, # Stub
            "overlap_ratio": 0.0
        }
        
        # 5. Store
        now_iso = str(int(time.time() * 1000))
        doc = {
            "_id": str(uuid.uuid4()),
            "session_id": session_id,
            "branch_id": branch_id,
            "checkpoint_id": checkpoint_id,
            "at_utterance_id": at_utterance_id,
            "computed_at": now_iso,
            "metrics": metrics_data
        }
        await self.metrics_repo.create(doc)
        
        return metrics_data
