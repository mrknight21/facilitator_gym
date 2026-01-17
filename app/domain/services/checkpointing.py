import uuid
import time
from typing import List, Dict, Any
from app.db.repos.checkpoint import CheckpointRepo
from app.domain.schemas import CheckpointOut

class Checkpointing:
    def __init__(self, checkpoint_repo: CheckpointRepo):
        self.checkpoint_repo = checkpoint_repo

    async def create_checkpoint(self, session_id: str, branch_id: str, at_utterance_id: str, state: Dict[str, Any]) -> str:
        checkpoint_id = str(uuid.uuid4())
        now_iso = str(int(time.time() * 1000))
        
        doc = {
            "_id": checkpoint_id,
            "session_id": session_id,
            "branch_id": branch_id,
            "at_utterance_id": at_utterance_id,
            "created_at": now_iso,
            "state": state
        }
        await self.checkpoint_repo.create(doc)
        return checkpoint_id

    async def list_checkpoints(self, session_id: str, branch_id: str) -> List[CheckpointOut]:
        docs = await self.checkpoint_repo.list_by_branch(session_id, branch_id)
        return [CheckpointOut(
            checkpoint_id=d["_id"],
            at_utterance_id=d["at_utterance_id"],
            created_at=d["created_at"],
            state=d["state"]
        ) for d in docs]
