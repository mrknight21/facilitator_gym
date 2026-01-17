import uuid
import time
from typing import Dict, Any, Optional
from app.db.repos.session import SessionRepo
from app.db.repos.branch import BranchRepo
from app.db.repos.utterance import UtteranceRepo
from app.db.repos.checkpoint import CheckpointRepo
from app.domain.services.transcript_resolver import TranscriptResolver

class ConductorWriter:
    def __init__(self, session_repo: SessionRepo, branch_repo: BranchRepo, 
                 utterance_repo: UtteranceRepo, checkpoint_repo: CheckpointRepo,
                 transcript_resolver: TranscriptResolver):
        self.session_repo = session_repo
        self.branch_repo = branch_repo
        self.utterance_repo = utterance_repo
        self.checkpoint_repo = checkpoint_repo
        self.transcript_resolver = transcript_resolver

    async def append_utterance_and_checkpoint(
        self,
        session_id: str,
        branch_id: str,
        kind: str,
        speaker_id: Optional[str],
        text: str,
        timing: Dict[str, int],
        state_snapshot: Dict[str, Any],
        event_id: str
    ) -> Dict[str, str]:
        # 1. Idempotency check
        existing = await self.utterance_repo.col.find_one({"event_id": event_id})
        if existing:
            ckpt = await self.checkpoint_repo.get_by_utterance(session_id, branch_id, existing["_id"])
            return {
                "utterance_id": existing["_id"],
                "checkpoint_id": ckpt["_id"] if ckpt else None,
                "display_id": "existing" # Placeholder
            }

        # 2. Get session
        session = await self.session_repo.get(session_id)
        if not session:
            raise ValueError("Session not found")
        
        # 3. Determine seq_in_branch
        utts = await self.utterance_repo.get_by_branch(session_id, branch_id)
        if utts:
            last_utt = utts[-1]
            seq_in_branch = last_utt.get("seq_in_branch", 0) + 1
            prev_id = last_utt["_id"]
        else:
            seq_in_branch = 1
            prev_id = None
            
        utterance_id = str(uuid.uuid4())
        checkpoint_id = str(uuid.uuid4())
        now_iso = str(int(time.time() * 1000))
        
        utt_doc = {
            "_id": utterance_id,
            "session_id": session_id,
            "branch_id": branch_id,
            "prev_utterance_id": prev_id,
            "seq_in_branch": seq_in_branch,
            "kind": kind,
            "speaker_id": speaker_id,
            "text": text,
            "timing": timing,
            "audio": {},
            "meta": {},
            "event_id": event_id,
            "created_at": now_iso
        }
        
        ckpt_doc = {
            "_id": checkpoint_id,
            "session_id": session_id,
            "branch_id": branch_id,
            "at_utterance_id": utterance_id,
            "created_at": now_iso,
            "state": state_snapshot
        }
        
        # 4. Write
        await self.utterance_repo.create(utt_doc)
        await self.checkpoint_repo.create(ckpt_doc)
        
        await self.session_repo.col.update_one(
            {"_id": session_id},
            {"$inc": {"write_version": 1}}
        )
        
        # 5. Compute display_id
        view = await self.transcript_resolver.get_transcript_view(session_id, branch_id)
        display_id = "unknown"
        for u in view.utterances:
            if u.utterance_id == utterance_id:
                display_id = u.display_id
                break
                
        return {
            "utterance_id": utterance_id,
            "checkpoint_id": checkpoint_id,
            "display_id": display_id
        }
