from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.domain.services.conductor_writer import ConductorWriter
from app.db.repos.session import SessionRepo
from app.db.repos.branch import BranchRepo
from app.db.repos.utterance import UtteranceRepo
from app.db.repos.checkpoint import CheckpointRepo
from app.domain.services.transcript_resolver import TranscriptResolver

router = APIRouter()

def get_writer():
    return ConductorWriter(
        SessionRepo(), BranchRepo(), UtteranceRepo(), CheckpointRepo(),
        TranscriptResolver(BranchRepo(), UtteranceRepo())
    )

class AppendReq(BaseModel):
    branch_id: str
    kind: str
    speaker_id: Optional[str]
    text: str
    timing: Dict[str, int]
    state_snapshot: Dict[str, Any]
    event_id: str

@router.post("/internal/sessions/{session_id}/append")
async def append_utterance(session_id: str, req: AppendReq, writer: ConductorWriter = Depends(get_writer)):
    try:
        return await writer.append_utterance_and_checkpoint(
            session_id, req.branch_id, req.kind, req.speaker_id, req.text, req.timing, req.state_snapshot, req.event_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
