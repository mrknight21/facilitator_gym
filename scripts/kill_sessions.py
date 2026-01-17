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
    
    sessions_to_kill = [
        "67e880e3-fde3-44ec-a98c-2197ca31085a"
    ]
    
    for session_id in sessions_to_kill:
        room_name = f"sess-{session_id}"
        print(f"Deleting room {room_name}...")
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
            print(f"Deleted {room_name}")
        except Exception as e:
            print(f"Failed to delete {room_name}: {e}")
            
    await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
