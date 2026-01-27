from fastapi import APIRouter, Depends, HTTPException
from app.domain.schemas import RewindReq, ContinueFromRewindReq, InterveneRes, RewindToReq, RewindPlanRes, ReplayUtteranceView
from app.db.repos.session import SessionRepo
from app.db.repos.utterance import UtteranceRepo
from app.domain.services.version_control import VersionControl
from app.domain.services.transcript_resolver import TranscriptResolver
from app.api.branches import get_vc
from app.db.repos.checkpoint import CheckpointRepo
from app.db.repos.branch import BranchRepo
from app.db.repos.replay_event_repo import ReplayEventRepo
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

@router.post("/sessions/{session_id}/rewind/plan", response_model=RewindPlanRes)
async def rewind_plan(
    session_id: str,
    req: RewindToReq,
    vc: VersionControl = Depends(get_vc),
    checkpoint_repo: CheckpointRepo = Depends(CheckpointRepo),
    utterance_repo: UtteranceRepo = Depends(UtteranceRepo),
    branch_repo: BranchRepo = Depends(BranchRepo),
    replay_event_repo: ReplayEventRepo = Depends(ReplayEventRepo)
):
    from app.domain.services.rewind_service import RewindService
    service = RewindService(vc, checkpoint_repo, utterance_repo, branch_repo, replay_event_repo)
    
    try:
        return await service.create_rewind_plan(
            session_id, req.branch_id, req.target_utterance_id, req.created_by
        )
    except ValueError as e:
        if "Checkpoint not found" in str(e):
             raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

