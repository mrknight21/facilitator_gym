import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.db.mongo import db, _client
from app.domain.schemas import CaseStudyOut

async def check_db():
    print("Checking DB connection...")
    try:
        # Ping
        await _client.admin.command('ping')
        print("Ping successful!")
        
        # Check collections
        colls = await db.list_collection_names()
        print(f"Collections: {colls}")
        
        # Check Case Studies validity
        cs_col = db["case_studies"]
        cursor = cs_col.find({})
        docs = await cursor.to_list(length=100)
        print(f"Found {len(docs)} case studies.")
        
        for doc in docs:
            print(f"Validating {doc.get('_id')}...")
            try:
                # Handle _id -> case_study_id mapping manually as repo does
                if "_id" in doc and "case_study_id" not in doc:
                    doc["case_study_id"] = doc["_id"]
                
                CaseStudyOut(**doc)
                print("VALID")
            except Exception as e:
                print(f"INVALID: {e}")

    except Exception as e:
        print(f"DB Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_db())
