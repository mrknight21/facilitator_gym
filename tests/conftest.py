import pytest
import mongomock
import asyncio
import os

# Set env vars for testing
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["LIVEKIT_URL"] = "ws://localhost:7880"
os.environ["LIVEKIT_API_KEY"] = "devkey"
os.environ["LIVEKIT_API_SECRET"] = "secret"

class AsyncCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def sort(self, *args, **kwargs):
        self._cursor.sort(*args, **kwargs)
        return self

    async def to_list(self, length):
        return list(self._cursor)
    
    def __aiter__(self):
        self._iter = iter(self._cursor)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

class AsyncCollection:
    def __init__(self, sync_col):
        self._col = sync_col

    async def insert_one(self, *args, **kwargs):
        return self._col.insert_one(*args, **kwargs)

    async def find_one(self, *args, **kwargs):
        return self._col.find_one(*args, **kwargs)
    
    async def update_one(self, *args, **kwargs):
        return self._col.update_one(*args, **kwargs)
        
    async def delete_one(self, *args, **kwargs):
        return self._col.delete_one(*args, **kwargs)

    def find(self, *args, **kwargs):
        cursor = self._col.find(*args, **kwargs)
        return AsyncCursor(cursor)
    
    async def count_documents(self, *args, **kwargs):
        return self._col.count_documents(*args, **kwargs)
        
    async def create_index(self, *args, **kwargs):
        return self._col.create_index(*args, **kwargs)

class AsyncDatabase:
    def __init__(self, sync_db):
        self._db = sync_db

    def __getitem__(self, name):
        return AsyncCollection(self._db[name])

@pytest.fixture
def mock_db(monkeypatch):
    client = mongomock.MongoClient()
    db = client.sim
    async_db = AsyncDatabase(db)
    
    monkeypatch.setattr("app.db.mongo.db", async_db)
    return async_db
