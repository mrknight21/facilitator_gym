from app.db.repos.base import BaseRepo
from typing import Any, Dict, List
import pymongo

class UtteranceRepo(BaseRepo):
    def __init__(self):
        super().__init__("utterances")

    async def ensure_indexes(self):
        # Unique index for non-seed utterances sequence
        # Note: partialFilterExpression might be needed if we want to enforce uniqueness only for non-seed
        # But for now, simple index is fine, or compound.
        await self.col.create_index(
            [("session_id", pymongo.ASCENDING), ("branch_id", pymongo.ASCENDING), ("seq_in_branch", pymongo.ASCENDING)],
            unique=True,
            partialFilterExpression={"kind": {"$ne": "seed"}}
        )
        # Index for seed lookup
        await self.col.create_index(
            [("session_id", pymongo.ASCENDING), ("branch_id", pymongo.ASCENDING), ("kind", pymongo.ASCENDING), ("seed_idx", pymongo.ASCENDING)]
        )

    async def create(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        await self.col.insert_one(doc)
        return doc

    async def get(self, utterance_id: str) -> Dict[str, Any] | None:
        return await self.col.find_one({"_id": utterance_id})

    async def get_by_branch(self, session_id: str, branch_id: str) -> List[Dict[str, Any]]:
        cursor = self.col.find({"session_id": session_id, "branch_id": branch_id}).sort("seq_in_branch", pymongo.ASCENDING)
        return await cursor.to_list(None)
