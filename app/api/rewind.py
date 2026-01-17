from fastapi import APIRouter, Depends, HTTPException
from app.domain.schemas import RewindReq, ContinueFromRewindReq, InterveneRes
from app.db.repos.session import SessionRepo
from app.domain.services.version_control import VersionControl
from app.api.branches import get_vc
from app.db.repos.checkpoint import CheckpointRepo
import uuid

router = APIRouter()

@router.post("/sessions/{session_id}/rewind")
async def rewind(session_id: str, req: RewindReq, session_repo: SessionRepo = Depends(SessionRepo)):
    # Verify checkpoint exists? Optional.
    await session_repo.update(session_id, {
        "playhead": {
            "branch_id": req.branch_id,
            "checkpoint_id": req.checkpoint_id
        }
    })
    return {"status": "ok"}

@router.post("/sessions/{session_id}/continue-from-rewind", response_model=InterveneRes)
async def continue_from_rewind(
    session_id: str, 
    req: ContinueFromRewindReq, 
    vc: VersionControl = Depends(get_vc),
    session_repo: SessionRepo = Depends(SessionRepo),
    checkpoint_repo: CheckpointRepo = Depends(CheckpointRepo)
):
    # Get playhead
    session = await session_repo.get(session_id)
    if not session or "playhead" not in session or not session["playhead"]:
        raise HTTPException(status_code=400, detail="No playhead set")
    
    ph = session["playhead"]
    
    # Get checkpoint to find utterance
    # Using find_one directly as CheckpointRepo.get_by_utterance is not by ID
    ckpt = await checkpoint_repo.col.find_one({"_id": ph["checkpoint_id"]})
    if not ckpt:
        raise HTTPException(status_code=400, detail="Checkpoint not found")

    # Fork
    try:
        fork_res = await vc.fork_branch(
            session_id, ph["branch_id"], ckpt["at_utterance_id"], ph["checkpoint_id"], req.created_by
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # Set active
    await vc.set_active_branch(session_id, fork_res.branch_id)
    
    # Clear playhead
    await session_repo.update(session_id, {"playhead": None})
    
    return InterveneRes(
        new_branch_id=fork_res.branch_id,
        intervention_utterance_id=ckpt["at_utterance_id"], 
        checkpoint_id=ph["checkpoint_id"]
    )
