import asyncio
import os
from livekit import api
from dotenv import load_dotenv

load_dotenv(".env.local")

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

async def main():
    lkapi = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    
    print("Listing active rooms...")
    results = await lkapi.room.list_rooms(api.ListRoomsRequest())
    
    for room in results.rooms:
        print(f"Name: {room.name}, ID: {room.sid}")
            
    await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
