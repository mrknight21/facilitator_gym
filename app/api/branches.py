from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.domain.schemas import ForkReq, ForkRes, SetActiveBranchReq, BranchOut
from app.domain.services.version_control import VersionControl
from app.db.repos.branch import BranchRepo
from app.db.repos.session import SessionRepo
from app.db.repos.utterance import UtteranceRepo
from app.db.repos.replay_event_repo import ReplayEventRepo

router = APIRouter()

def get_vc():
    return VersionControl(BranchRepo(), SessionRepo())

@router.post("/sessions/{session_id}/fork", response_model=ForkRes)
async def fork_branch(session_id: str, req: ForkReq, vc: VersionControl = Depends(get_vc)):
    try:
        return await vc.fork_branch(
            session_id, req.parent_branch_id, req.from_utterance_id, req.from_checkpoint_id, req.created_by
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sessions/{session_id}/active-branch")
async def set_active_branch(session_id: str, req: SetActiveBranchReq, vc: VersionControl = Depends(get_vc)):
    try:
        await vc.set_active_branch(session_id, req.branch_id)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sessions/{session_id}/branches", response_model=List[BranchOut])
async def list_branches(session_id: str, vc: VersionControl = Depends(get_vc)):
    return await vc.list_branches(session_id)


@router.get("/sessions/{session_id}/branches/{branch_id}/materialized_timeline")
async def get_materialized_timeline(
    session_id: str, 
    branch_id: str,
    branch_repo: BranchRepo = Depends(BranchRepo),
    utterance_repo: UtteranceRepo = Depends(UtteranceRepo),
    replay_event_repo: ReplayEventRepo = Depends(ReplayEventRepo)
):
    from app.domain.services.transcript_resolver import TranscriptResolver
    from app.domain.services.materialize_timeline import MaterializeTimelineService
    
    resolver = TranscriptResolver(branch_repo, utterance_repo)
    service = MaterializeTimelineService(branch_repo, utterance_repo, replay_event_repo, resolver)
    
    return await service.get_materialized_timeline(session_id, branch_id)
