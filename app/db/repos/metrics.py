from app.db.repos.base import BaseRepo
from typing import Any, Dict, Optional
import pymongo

class MetricsRepo(BaseRepo):
    def __init__(self):
        super().__init__("metrics")

    async def ensure_indexes(self):
        await self.col.create_index(
            [("session_id", pymongo.ASCENDING), ("branch_id", pymongo.ASCENDING), ("checkpoint_id", pymongo.ASCENDING)]
        )

    async def create(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        await self.col.insert_one(doc)
        return doc

    async def get_by_checkpoint(self, session_id: str, branch_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({
            "session_id": session_id,
            "branch_id": branch_id,
            "checkpoint_id": checkpoint_id
        })
