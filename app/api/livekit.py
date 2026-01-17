from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.livekit.tokens import mint_token, build_room_name

router = APIRouter()

class TokenReq(BaseModel):
    identity: str
    role: str # facilitator, participant

class AgentTokenReq(BaseModel):
    identity: str
    agent_name: str

@router.post("/sessions/{session_id}/token")
async def get_token(session_id: str, req: TokenReq):
    room_name = build_room_name(session_id)
    # Role logic: facilitator can publish everything?
    # For MVP, allow publish/subscribe for everyone.
    token = mint_token(req.identity, room_name, True, True, True)
    return {"token": token, "room_name": room_name}

@router.post("/sessions/{session_id}/agent-token")
async def get_agent_token(session_id: str, req: AgentTokenReq):
    room_name = build_room_name(session_id)
    token = mint_token(req.identity, room_name, True, True, True)
    return {"token": token, "room_name": room_name}
