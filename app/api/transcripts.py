from fastapi import APIRouter, Depends, HTTPException
from app.domain.schemas import TranscriptViewOut
from app.domain.services.transcript_resolver import TranscriptResolver
from app.db.repos.branch import BranchRepo
from app.db.repos.utterance import UtteranceRepo

router = APIRouter()

def get_resolver():
    return TranscriptResolver(BranchRepo(), UtteranceRepo())

@router.get("/sessions/{session_id}/branches/{branch_id}/transcript", response_model=TranscriptViewOut)
async def get_transcript(session_id: str, branch_id: str, resolver: TranscriptResolver = Depends(get_resolver)):
    return await resolver.get_transcript_view(session_id, branch_id)
