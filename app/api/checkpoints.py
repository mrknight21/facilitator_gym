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

@router.get("/sessions/{session_id}/branches/{branch_id}/checkpoint", response_model=CheckpointOut)
async def get_checkpoint_by_utterance(
    session_id: str, 
    branch_id: str, 
    at_utterance_id: str, 
    repo: CheckpointRepo = Depends(CheckpointRepo)
):
    ckpt = await repo.get_by_utterance(session_id, branch_id, at_utterance_id)
    if not ckpt:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Checkpoint not found for this utterance")
    return ckpt
