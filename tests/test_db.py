import pytest
from app.db.repos.base import BaseRepo

class MockRepo(BaseRepo):
    def __init__(self):
        super().__init__("test_col")

@pytest.mark.asyncio
async def test_mock_db_crud(mock_db):
    repo = MockRepo()
    
    # Insert
    await repo.col.insert_one({"_id": "1", "val": "a"})
    
    # Find one
    doc = await repo.col.find_one({"_id": "1"})
    assert doc["val"] == "a"
    
    # Find many
    cursor = repo.col.find({})
    docs = await cursor.to_list(None)
    assert len(docs) == 1
