import asyncio
import os
import json
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
# Load env
# Try root .env.local first, then frontend/.env.local
start_path = Path(".")
env_path = start_path / ".env.local"
if not env_path.exists():
    env_path = start_path / "frontend" / ".env.local"

print(f"Loading env from: {env_path.absolute()}")
load_dotenv(env_path)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
print(f"MONGO_URI: {MONGO_URI}")
DB_NAME = os.getenv("MONGO_DB", "sim")

async def seed():
    print(f"Connecting to {MONGO_URI}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # 1. Base Dir
    base_dir = Path("case_studies")
    if not base_dir.exists():
        print(f"No case_studies dir found at {base_dir.absolute()}")
        return

    # 2. Iterate
    for cs_dir in base_dir.iterdir():
        if not cs_dir.is_dir(): continue
        
        meta_path = cs_dir / "metadata.json"
        if not meta_path.exists(): continue
        
        with open(meta_path, "r") as f:
            cs = json.load(f)
            
        print(f"Processing {cs['id']}...")
        
        # 3. Inject Audio Paths
        audio_dir = cs_dir / "audio"
        for seed in cs.get("seed_utterances", []):
            speaker = seed["speaker"].lower()
            fname = f"seed_{seed['seed_idx']}_{speaker}.mp3"
            fpath = audio_dir / fname
            if fpath.exists():
                seed["audio_url"] = str(fpath.absolute())
                print(f"  Found audio for seed {seed['seed_idx']}: {fpath.name}")
            else:
                print(f"  No audio for seed {seed['seed_idx']}")

        # 4. Upsert
        print("  Inserting case study...")
        await db.case_studies.replace_one({"_id": cs["id"]}, cs, upsert=True)
    
    print("Done!")

if __name__ == "__main__":
    asyncio.run(seed())
