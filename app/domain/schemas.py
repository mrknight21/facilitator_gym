from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from enum import Enum
from pydantic import BaseModel, Field


# -------------------------
# Common / primitives
# -------------------------

class Timing(BaseModel):
    t_start_ms: int = 0
    t_end_ms: int = 0
    wall_start_ts: Optional[float] = None  # Wall-clock timestamp (for debugging)
    wall_end_ts: Optional[float] = None


class AudioRef(BaseModel):
    ref: Optional[str] = None
    offset_ms: Optional[int] = None
    duration_ms: Optional[int] = None
    url: Optional[str] = None # Direct URL/Path to audio file


UtteranceKind = Literal["seed", "ai", "user_intervention", "system_silence"]
Intent = Literal["challenge", "support", "ask", "answer", "summarize", "stay_silent"]


# -------------------------
# API Schemas
# -------------------------

class SeedUtteranceIn(BaseModel):
    seed_idx: int = Field(..., ge=1)
    speaker: str
    text: str
    audio_url: Optional[str] = None


class CaseStudyCreate(BaseModel):
    case_study_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    seed_utterances: List[SeedUtteranceIn]


class CaseStudyOut(BaseModel):
    case_study_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    seed_utterances: List[SeedUtteranceIn]


class SessionConfig(BaseModel):
    participants: List[str] = Field(default_factory=list)  # ["alice","bob","user"]
    auction_policy: str = "v1"
    silence_threshold: float = Field(0.35, ge=0.0, le=1.0)
    max_turn_seconds: float = Field(10.0, gt=0.0)


class SessionStartReq(BaseModel):
    case_study_id: str
    created_by: str
    config: SessionConfig


class SessionStartRes(BaseModel):
    session_id: str
    root_branch_id: str
    active_branch_id: str
    last_seed_utterance_id: Optional[str] = None
    room_name: str


class ForkReq(BaseModel):
    parent_branch_id: str
    from_utterance_id: Optional[str] = None
    from_checkpoint_id: Optional[str] = None
    created_by: str


class ForkRes(BaseModel):
    branch_id: str
    parent_branch_id: str
    fork_from_utterance_id: Optional[str] = None
    fork_from_checkpoint_id: Optional[str] = None
    branch_label: str


class SetActiveBranchReq(BaseModel):
    branch_id: str


class InterveneReq(BaseModel):
    parent_branch_id: str
    at_utterance_id: str
    created_by: str
    intervention_text: str


class InterveneRes(BaseModel):
    new_branch_id: str
    intervention_utterance_id: str
    checkpoint_id: str


class RewindReq(BaseModel):
    branch_id: str
    checkpoint_id: str


class RewindToReq(BaseModel):
    branch_id: str
    target_utterance_id: str
    created_by: str


class UtteranceView(BaseModel):
    utterance_id: str
    speaker_id: Optional[str]
    kind: UtteranceKind
    text: str
    timing: Timing = Field(default_factory=Timing)
    audio: AudioRef = Field(default_factory=AudioRef)
    display_id: str


class ReplayUtteranceView(UtteranceView):
    pass # Reusing UtteranceView as it has AudioRef


class ReplayStatus(str, Enum):
    PLANNED = "planned"
    REPLAYING = "replaying"
    COMPLETED = "completed"
    CANCELED = "canceled"


class ReplayEvent(BaseModel):
    replay_event_id: str
    session_id: str
    from_branch_id: str
    to_branch_id: str
    target_turn_id: str
    replayed_turn_ids: List[str]
    handoff_at_turn_id: Optional[str] = None
    handoff_reason: Literal["HIT_FACILITATOR_TURN", "END_OF_TIMELINE"]
    created_at: str
    created_by: str
    status: ReplayStatus
    
    # Diagnostics
    first_audio_start_ts: Optional[float] = None
    last_audio_end_ts: Optional[float] = None
    canceled_at_turn_id: Optional[str] = None


class RewindPlanRes(BaseModel):
    new_branch_id: str
    fork_checkpoint_id: str
    target_utterance_id: str
    replay_utterances: List[ReplayUtteranceView]
    handoff_reason: Literal["HIT_FACILITATOR_TURN", "END_OF_TIMELINE"]
    handoff_at_utterance_id: Optional[str] = None
    replay_event_id: str # Added for tracking


class ContinueFromRewindReq(BaseModel):
    created_by: str
    note: Optional[str] = None


class BranchOut(BaseModel):
    branch_id: str
    parent_branch_id: Optional[str] = None
    fork_from_utterance_id: Optional[str] = None
    fork_from_checkpoint_id: Optional[str] = None
    branch_label: str
    created_at: Optional[str] = None




class TranscriptViewOut(BaseModel):
    session_id: str
    branch_id: str
    utterances: List[UtteranceView]


class CheckpointOut(BaseModel):
    checkpoint_id: str
    at_utterance_id: str
    created_at: str
    state: Dict[str, Any]


class MetricsOut(BaseModel):
    checkpoint_id: str
    at_utterance_id: str
    computed_at: str
    metrics: Dict[str, Any]


# -------------------------
# LiveKit Data Messages
# -------------------------

class MsgBase(BaseModel):
    v: int = 1
    session_id: str
    branch_id: str


class TurnBidMsg(MsgBase):
    agent_id: str
    bid: float = Field(..., ge=0.0, le=1.0)
    intent: Intent
    rationale: str = ""
    at_utterance_id: Optional[str] = None


class TurnGrantConstraints(BaseModel):
    max_sentences: int = 2
    end_with_question: bool = True


class TurnGrantContext(BaseModel):
    last_utterance_id: Optional[str] = None
    agenda: str = ""
    short_summary: str = ""
    constraints: TurnGrantConstraints = Field(default_factory=TurnGrantConstraints)


class TurnGrantMsg(MsgBase):
    to: str
    grant_id: str
    context: TurnGrantContext


class TurnRevokeMsg(MsgBase):
    to: str
    reason: Literal["user_interrupt", "timeout", "policy"]


class UttSpokenMsg(MsgBase):
    # agent -> conductor. This is what conductor will persist.
    speaker_id: str
    kind: Literal["ai", "user_intervention", "system_silence"] = "ai"
    text: str
    timing: Timing = Field(default_factory=Timing)
    meta: Dict[str, Any] = Field(default_factory=dict)


class UttFinalMsg(MsgBase):
    checkpoint_id: str
    utterance: UtteranceView


class MetricsUpdateMsg(MsgBase):
    checkpoint_id: str
    metrics: Dict[str, Any]
