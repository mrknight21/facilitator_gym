from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

_client = AsyncIOMotorClient(settings.MONGO_URI)
db = _client[settings.MONGO_DB]
