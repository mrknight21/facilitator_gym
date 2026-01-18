from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class MsgType(str, Enum):
    # Conductor -> Participant
    INIT = "init"
    SPEAK_CMD = "speak_cmd"
    STOP_CMD = "stop_cmd"
    
    # Participant -> Conductor
    PLAYBACK_DONE = "playback_done"
    PLAYBACK_STOPPED = "playback_stopped"
    
    # Facilitator (Frontend) -> Conductor
    FAC_JOIN = "fac_join"
    FAC_START = "fac_start" # Push-to-talk start
    FAC_END = "fac_end"     # Push-to-talk end / finish utterance
    FINISH = "finish"       # End session

class AgentPacket(BaseModel):
    """
    Standard envelope for all data messages in the simulation.
    """
    type: MsgType
    session_id: str
    turn_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

# Payload Schemas (Standardizing what goes into 'payload')

class SpeakCmdPayload(BaseModel):
    text: str
    speaker_id: str # The identity who should speak (useful if broadcast)
    audio_url: Optional[str] = None

class PlaybackDonePayload(BaseModel):
    speaker_id: str
    duration_ms: int
    interrupted: bool = False

class FacAudioPayload(BaseModel):
    # For metadata about the facilitator's speech if handled largely by backend STT
    pass
