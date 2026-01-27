#!/usr/bin/env python3
"""
Cleanup script for development data.
Removes cached audio, MongoDB data (sessions, branches, utterances, checkpoints, etc.)
"""

import asyncio
import os
import shutil
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(".env.local")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "facilitator_gym")

# Audio cache directories
AUDIO_CACHE_DIRS = [
    "audio_cache",
    "tmp_audio",
    ".audio_cache",
]

# MongoDB collections to clear (except case_studies which is seed data)
COLLECTIONS_TO_CLEAR = [
    "sessions",
    "branches",
    "utterances",
    "checkpoints",
    "metrics",
    "replay_events",
]

async def clear_mongodb():
    """Clear development data from MongoDB."""
    print(f"Connecting to MongoDB: {MONGO_URI}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    
    for col_name in COLLECTIONS_TO_CLEAR:
        col = db[col_name]
        count = await col.count_documents({})
        if count > 0:
            result = await col.delete_many({})
            print(f"  ✓ Cleared {col_name}: {result.deleted_count} documents")
        else:
            print(f"  - {col_name}: already empty")
    
    client.close()
    print("MongoDB cleanup complete.")

def clear_audio_cache():
    """Remove cached audio files."""
    print("\nClearing audio cache directories...")
    for cache_dir in AUDIO_CACHE_DIRS:
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"  ✓ Removed {cache_dir}/")
        else:
            print(f"  - {cache_dir}: not found")
    print("Audio cache cleanup complete.")

def main():
    print("=" * 50)
    print("Facilitator Gym - Development Data Cleanup")
    print("=" * 50)
    print()
    
    # Confirm
    response = input("This will DELETE all sessions, branches, utterances, checkpoints, and cached audio.\nContinue? [y/N]: ")
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    print()
    print("Clearing MongoDB...")
    asyncio.run(clear_mongodb())
    
    clear_audio_cache()
    
    print()
    print("✓ Cleanup complete!")

if __name__ == "__main__":
    main()
