import sys
import typing

# Python 3.9 Compatibility Patch
if sys.version_info < (3, 10):
    try:
        from typing_extensions import TypeAlias
        typing.TypeAlias = TypeAlias
    except ImportError:
        pass

import asyncio
import os
from livekit import api
from dotenv import load_dotenv

load_dotenv(".env.local")

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

async def main():
    print(f"Connecting to {LIVEKIT_URL}...")
    lkapi = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    
    try:
        print("Listing rooms...")
        results = await lkapi.room.list_rooms(api.ListRoomsRequest())
        rooms = results.rooms
        
        if not rooms:
            print("No active rooms found.")
            return

        print(f"Found {len(rooms)} active rooms.")
        for room in rooms:
            print(f"Deleting room: {room.name} ({room.sid})")
            try:
                await lkapi.room.delete_room(api.DeleteRoomRequest(room=room.name))
                print(f"  ✓ Deleted {room.name}")
            except Exception as e:
                print(f"  ✗ Failed to delete {room.name}: {e}")
                
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
