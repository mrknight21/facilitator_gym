from fastapi import APIRouter, Depends
from typing import List
from app.domain.schemas import CheckpointOut
from app.domain.services.checkpointing import Checkpointing
from app.db.repos.checkpoint import CheckpointRepo

router = APIRouter()

def get_checkpointing():
    return Checkpointing(CheckpointRepo())

@router.get("/sessions/{session_id}/branches/{branch_id}/checkpoints", response_model=List[CheckpointOut])
async def list_checkpoints(session_id: str, branch_id: str, cp: Checkpointing = Depends(get_checkpointing)):
    return await cp.list_checkpoints(session_id, branch_id)
