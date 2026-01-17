from app.db.repos.base import BaseRepo
from typing import Any, Dict, List
import pymongo

class BranchRepo(BaseRepo):
    def __init__(self):
        super().__init__("branches")

    async def ensure_indexes(self):
        await self.col.create_index([("session_id", pymongo.ASCENDING), ("parent_branch_id", pymongo.ASCENDING)])

    async def create(self, branch_data: Dict[str, Any]) -> Dict[str, Any]:
        await self.col.insert_one(branch_data)
        return branch_data

    async def get(self, branch_id: str) -> Dict[str, Any] | None:
        return await self.col.find_one({"_id": branch_id})

    async def list_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        cursor = self.col.find({"session_id": session_id})
        return await cursor.to_list(None)
