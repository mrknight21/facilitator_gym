import uuid
import time
from typing import List, Dict, Any
from app.db.repos.branch import BranchRepo
from app.db.repos.session import SessionRepo
from app.domain.schemas import ForkRes, BranchOut

class VersionControl:
    def __init__(self, branch_repo: BranchRepo, session_repo: SessionRepo):
        self.branch_repo = branch_repo
        self.session_repo = session_repo

    async def fork_branch(self, session_id: str, parent_branch_id: str, 
                          from_utterance_id: str | None, from_checkpoint_id: str | None, 
                          created_by: str) -> ForkRes:
        # Verify parent branch exists
        parent = await self.branch_repo.get(parent_branch_id)
        if not parent:
            raise ValueError("Parent branch not found")
        
        # Create new branch
        branch_id = str(uuid.uuid4())
        # Generate label: simple count or random
        label = f"alt-{branch_id[:4]}"
        
        now_iso = str(int(time.time() * 1000))
        
        branch_doc = {
            "_id": branch_id,
            "session_id": session_id,
            "parent_branch_id": parent_branch_id,
            "fork_from_utterance_id": from_utterance_id,
            "fork_from_checkpoint_id": from_checkpoint_id,
            "branch_label": label,
            "created_at": now_iso
        }
        await self.branch_repo.create(branch_doc)
        
        return ForkRes(
            branch_id=branch_id,
            parent_branch_id=parent_branch_id,
            fork_from_utterance_id=from_utterance_id,
            fork_from_checkpoint_id=from_checkpoint_id,
            branch_label=label
        )

    async def set_active_branch(self, session_id: str, branch_id: str) -> None:
        # Verify branch exists
        branch = await self.branch_repo.get(branch_id)
        if not branch:
            raise ValueError("Branch not found")
        if branch["session_id"] != session_id:
            raise ValueError("Branch does not belong to session")
            
        await self.session_repo.update(session_id, {"active_branch_id": branch_id})

    async def list_branches(self, session_id: str) -> List[BranchOut]:
        docs = await self.branch_repo.list_by_session(session_id)
        return [BranchOut(
            branch_id=d["_id"],
            parent_branch_id=d.get("parent_branch_id"),
            fork_from_utterance_id=d.get("fork_from_utterance_id"),
            fork_from_checkpoint_id=d.get("fork_from_checkpoint_id"),
            branch_label=d["branch_label"],
            created_at=d.get("created_at")
        ) for d in docs]
