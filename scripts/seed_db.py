import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(".env.local")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "sim")

async def seed():
    print(f"Connecting to {MONGO_URI}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Case Study Data
    cs_payload = {
        "_id": "cs_e2e",
        "case_study_id": "cs_e2e", # Duplicate for consistency with schema if needed, but repo handles _id
        "title": "Difficult Conversation: The Project Delay",
        "description": "A high-stakes meeting where three team members discuss a significant delay in the project timeline. Tensions are high as they blame each other for the setbacks.",
        "participants": ["Alice (Project Manager)", "Bob (Lead Dev)", "Charlie (QA Lead)"],
        "seed_utterances": [
            {"seed_idx": 1, "speaker": "alice", "text": "Hello everyone, we need to talk about the timeline."},
            {"seed_idx": 2, "speaker": "bob", "text": "I know what you're going to say, Alice. It's not my fault."},
            {"seed_idx": 3, "speaker": "charlie", "text": "Let's just focus on solutions, please."}
        ]
    }
    
    print("Inserting case study...")
    await db.case_studies.replace_one({"_id": "cs_e2e"}, cs_payload, upsert=True)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(seed())
