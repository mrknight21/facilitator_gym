import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load env for OpenAI Key
# Try root .env.local first, then frontend/.env.local
start_path = Path(".")
env_path = start_path / ".env.local"
if not env_path.exists():
    env_path = start_path / "frontend" / ".env.local"

print(f"Loading env from: {env_path.absolute()}")
load_dotenv(env_path)

# Define Base Dir
BASE_DIR = Path("case_studies")
BASE_DIR.mkdir(exist_ok=True)

# Define Case Studies Data (Source of Truth)
CASE_STUDIES = [
    {
        "id": "cs_e2e",
        "title": "Difficult Conversation: The Project Delay",
        "description": "A high-stakes meeting where three team members discuss a significant delay in the project timeline.",
        "participants": ["Alice (Project Manager)", "Bob (Lead Dev)", "Charlie (QA Lead)"],
        "seed_utterances": [
            {"seed_idx": 1, "speaker": "alice", "text": "Hello everyone, we need to talk about the timeline."},
            {"seed_idx": 2, "speaker": "bob", "text": "I know what you're going to say, Alice. It's not my fault."},
            {"seed_idx": 3, "speaker": "charlie", "text": "Let's just focus on solutions, please."}
        ]
    }
]

VOICE_MAP = {
    "alice": "alloy",
    "bob": "onyx",
    "charlie": "fable"
}

async def generate_assets():
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    for cs in CASE_STUDIES:
        cs_dir = BASE_DIR / cs["id"]
        audio_dir = cs_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Processing Case Study: {cs['title']} ({cs['id']})")
        
        # 1. Save Metadata (JSON)
        meta_path = cs_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(cs, f, indent=2)
        print(f"  Saved metadata to {meta_path}")
        
        # 2. Generate Audio
        for seed in cs["seed_utterances"]:
            speaker = seed["speaker"].lower()
            text = seed["text"]
            voice = VOICE_MAP.get(speaker, "alloy")
            
            filename = f"seed_{seed['seed_idx']}_{speaker}.mp3"
            filepath = audio_dir / filename
            
            if filepath.exists():
                print(f"  Skipping {filename} (exists)")
                continue
                
            print(f"  Generating audio for {speaker}: '{text}' using voice {voice}...")
            
            try:
                response = await client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text
                )
                response.stream_to_file(filepath)
                print(f"  Saved to {filepath}")
            except Exception as e:
                print(f"  Failed to generate audio for {speaker}: {e}")

if __name__ == "__main__":
    asyncio.run(generate_assets())
