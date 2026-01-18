import uuid
import time
from typing import Dict, Any
from app.db.repos.session import SessionRepo
from app.db.repos.branch import BranchRepo
from app.db.repos.utterance import UtteranceRepo
from app.db.repos.case_study import CaseStudyRepo
from app.domain.schemas import SessionStartReq, SessionStartRes

class SessionManager:
    def __init__(self, session_repo: SessionRepo, branch_repo: BranchRepo, 
                 utterance_repo: UtteranceRepo, case_study_repo: CaseStudyRepo):
        self.session_repo = session_repo
        self.branch_repo = branch_repo
        self.utterance_repo = utterance_repo
        self.case_study_repo = case_study_repo

    async def start_session(self, req: SessionStartReq) -> SessionStartRes:
        # 1. Get case study
        cs = await self.case_study_repo.get(req.case_study_id)
        if not cs:
            raise ValueError("Case study not found")

        # 2. Create session
        session_id = str(uuid.uuid4())
        room_name = f"sess-{session_id}"
        root_branch_id = str(uuid.uuid4())
        now_iso = str(int(time.time() * 1000)) # Simple timestamp
        
        session_doc = {
            "_id": session_id,
            "case_study_id": req.case_study_id,
            "created_by": req.created_by,
            "created_at": now_iso,
            "status": "active",
            "root_branch_id": root_branch_id,
            "active_branch_id": root_branch_id,
            "room_id": room_name,
            "config": req.config.model_dump(),
            "write_version": 0
        }
        await self.session_repo.create(session_doc)

        # 3. Create root branch
        branch_doc = {
            "_id": root_branch_id,
            "session_id": session_id,
            "parent_branch_id": None,
            "fork_from_utterance_id": None,
            "fork_from_checkpoint_id": None,
            "branch_label": "main",
            "created_at": now_iso
        }
        await self.branch_repo.create(branch_doc)

        # 4. Clone seed utterances
        last_seed_id = None
        prev_id = None
        for seed in cs.seed_utterances:
            utt_id = str(uuid.uuid4())
            utt_doc = {
                "_id": utt_id,
                "session_id": session_id,
                "branch_id": root_branch_id,
                "prev_utterance_id": prev_id,
                "seq_in_branch": seed.seed_idx,
                "kind": "seed",
                "speaker_id": seed.speaker,
                "text": seed.text,
                "seed_idx": seed.seed_idx,
                "timing": {"t_start_ms": 0, "t_end_ms": 0},
                "audio": {"url": seed.audio_url} if seed.audio_url else {},
                "meta": {},
                "created_at": now_iso
            }
            await self.utterance_repo.create(utt_doc)
            prev_id = utt_id
            last_seed_id = utt_id

        return SessionStartRes(
            session_id=session_id,
            root_branch_id=root_branch_id,
            active_branch_id=root_branch_id,
            last_seed_utterance_id=last_seed_id,
            room_name=room_name
        )
