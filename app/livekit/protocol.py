from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class MsgType(str, Enum):
    # Conductor -> Participant
    INIT = "init"
    SPEAK_CMD = "speak_cmd"
    PLAY_ASSET_CMD = "play_asset_cmd"
    STOP_CMD = "stop_cmd"
    
    # Participant -> Conductor
    PLAYBACK_DONE = "playback_done"
    PLAYBACK_STOPPED = "playback_stopped"
    
    # Facilitator (Frontend) -> Conductor
    FAC_JOIN = "fac_join"
    FAC_START = "fac_start" # Push-to-talk start
    FAC_END = "fac_end"     # Push-to-talk end / finish utterance
    FINISH = "finish"       # End session

    # Server -> Client (Verification)
    MIC_SEEN = "mic_seen"
    # ACK for PTT Start
    FAC_ACK = "fac_ack"
    
    # Worker -> Conductor (Internal/Broadcast)
    TRANSCRIPT_COMPLETE = "transcript_complete"

    # Broadcast Silence
    SILENCE_START = "silence_start"
    
    # Rewind Commands (Epic 3)
    TIME_STOP = "time_stop"
    REWIND_TO = "rewind_to"
    REWIND_CANCEL = "rewind_cancel"
    
    # Replay Progress (Epic 5)
    REPLAY_PROGRESS = "replay_progress"
    
    # Clock Sync (Session Timekeeping)
    CLOCK_SYNC = "clock_sync"
    CLOCK_PAUSE = "clock_pause"
    CLOCK_RESUME = "clock_resume"
    CLOCK_REWIND = "clock_rewind"
    TURN_PLAYBACK_TIMES = "turn_playback_times"

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

class PlayAssetCmdPayload(BaseModel):
    audio_url: str
    speaker_id: str
    text: Optional[str] = None
    turn_id: Optional[str] = None

class PlaybackDonePayload(BaseModel):
    speaker_id: str
    duration_ms: int
    interrupted: bool = False
    audio_url: Optional[str] = None

class FacAudioPayload(BaseModel):
    # For metadata about the facilitator's speech if handled largely by backend STT
    pass

class RewindToPayload(BaseModel):
    target_utterance_id: str
    created_by: str = "user"
