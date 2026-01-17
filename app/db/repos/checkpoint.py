from app.db.repos.base import BaseRepo
from typing import Any, Dict, List
import pymongo

class CheckpointRepo(BaseRepo):
    def __init__(self):
        super().__init__("checkpoints")

    async def ensure_indexes(self):
        await self.col.create_index(
            [("session_id", pymongo.ASCENDING), ("branch_id", pymongo.ASCENDING), ("at_utterance_id", pymongo.ASCENDING)]
        )

    async def create(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        await self.col.insert_one(doc)
        return doc

    async def get_by_utterance(self, session_id: str, branch_id: str, utterance_id: str) -> Dict[str, Any] | None:
        return await self.col.find_one({
            "session_id": session_id,
            "branch_id": branch_id,
            "at_utterance_id": utterance_id
        })

    async def list_by_branch(self, session_id: str, branch_id: str) -> List[Dict[str, Any]]:
        cursor = self.col.find({"session_id": session_id, "branch_id": branch_id}).sort("created_at", pymongo.ASCENDING)
        return await cursor.to_list(None)
