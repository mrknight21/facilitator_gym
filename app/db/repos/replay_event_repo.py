from app.db.repos.base import BaseRepo
from typing import Any, Dict, List, Optional
import pymongo

class ReplayEventRepo(BaseRepo):
    def __init__(self):
        super().__init__("replay_events")

    async def ensure_indexes(self):
        await self.col.create_index(
            [("session_id", pymongo.ASCENDING), ("to_branch_id", pymongo.ASCENDING)]
        )
        await self.col.create_index("replay_event_id", unique=True)

    async def create(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        await self.col.insert_one(doc)
        return doc

    async def get(self, replay_event_id: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"replay_event_id": replay_event_id})

    async def update_status(self, replay_event_id: str, status: str, **kwargs):
        update_fields = {"status": status}
        update_fields.update(kwargs)
        await self.col.update_one(
            {"replay_event_id": replay_event_id},
            {"$set": update_fields}
        )

    async def list_by_branch(self, session_id: str, branch_id: str) -> List[Dict[str, Any]]:
        # Find events that target this branch (to_branch_id)
        cursor = self.col.find({
            "session_id": session_id, 
            "to_branch_id": branch_id
        }).sort("created_at", pymongo.ASCENDING)
        return await cursor.to_list(None)
