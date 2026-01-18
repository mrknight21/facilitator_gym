from app.db.repos.base import BaseRepo
from typing import Any, Dict, Optional

class SessionRepo(BaseRepo):
    def __init__(self):
        super().__init__("sessions")

    async def create(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        # session_data should include _id
        await self.col.insert_one(session_data)
        return session_data

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"_id": session_id})

    async def update(self, session_id: str, update_dict: Dict[str, Any]) -> None:
        await self.col.update_one({"_id": session_id}, {"$set": update_dict})
