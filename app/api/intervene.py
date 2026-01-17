from fastapi import APIRouter, Depends, HTTPException
from app.domain.schemas import InterveneReq, InterveneRes
from app.domain.services.version_control import VersionControl
from app.domain.services.conductor_writer import ConductorWriter
from app.domain.services.checkpointing import Checkpointing
from app.api.branches import get_vc
from app.api.utterances import get_writer
from app.api.checkpoints import get_checkpointing

router = APIRouter()

@router.post("/sessions/{session_id}/intervene", response_model=InterveneRes)
async def intervene(
    session_id: str, 
    req: InterveneReq, 
    vc: VersionControl = Depends(get_vc),
    writer: ConductorWriter = Depends(get_writer),
    cp: Checkpointing = Depends(get_checkpointing)
):
    # 1. Fork
    try:
        fork_res = await vc.fork_branch(
            session_id, req.parent_branch_id, req.at_utterance_id, None, req.created_by
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Insert intervention utterance
    event_id = f"intervention-{fork_res.branch_id}"
    
    # TODO: Hydrate state from previous checkpoint
    state_snapshot = {} 
    
    append_res = await writer.append_utterance_and_checkpoint(
        session_id=session_id,
        branch_id=fork_res.branch_id,
        kind="user_intervention",
        speaker_id="facilitator", 
        text=req.intervention_text,
        timing={"t_start_ms": 0, "t_end_ms": 0},
        state_snapshot=state_snapshot,
        event_id=event_id
    )
    
    # 3. Set active branch
    await vc.set_active_branch(session_id, fork_res.branch_id)
    
    return InterveneRes(
        new_branch_id=fork_res.branch_id,
        intervention_utterance_id=append_res["utterance_id"],
        checkpoint_id=append_res["checkpoint_id"]
    )
