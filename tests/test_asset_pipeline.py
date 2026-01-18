import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.livekit.conductor import Conductor
from app.domain.services.session_manager import SessionManager, SessionStartReq
from app.domain.schemas import SessionConfig, SeedUtteranceIn
from app.livekit.protocol import MsgType, AgentPacket, SpeakCmdPayload
import json

@pytest.fixture
def mock_repos():
    return {
        "session": AsyncMock(),
        "branch": AsyncMock(),
        "utterance": AsyncMock(),
        "case_study": AsyncMock()
    }

@pytest.fixture
def mock_room():
    room = MagicMock()
    room.local_participant.publish_data = AsyncMock()
    return room

@pytest.mark.asyncio
async def test_session_creation_persists_audio_url(mock_repos):
    """Test that SessionManager preserves audio_url from Case Study."""
    sm = SessionManager(
        mock_repos["session"], mock_repos["branch"], 
        mock_repos["utterance"], mock_repos["case_study"]
    )
    
    # Mock Case Study with audio URL
    mock_cs = MagicMock()
    mock_cs.seed_utterances = [
        SeedUtteranceIn(seed_idx=1, speaker="alice", text="Hi", audio_url="/tmp/audio.mp3")
    ]
    mock_repos["case_study"].get.return_value = mock_cs
    
    # Start Session
    req = SessionStartReq(
        case_study_id="cs1", 
        created_by="user1", 
        config=SessionConfig()
    )
    await sm.start_session(req)
    
    # Verify Utterance creation
    call_args = mock_repos["utterance"].create.call_args[0][0]
    assert call_args["audio"]["url"] == "/tmp/audio.mp3"

@pytest.mark.asyncio
async def test_conductor_sends_audio_url_packet(mock_room):
    """Test that Conductor includes audio_url in SPEAK_CMD."""
    # Mock services
    writer = AsyncMock()
    metrics = AsyncMock()
    resolver = AsyncMock()
    
    # Mock transcript view with audio URL
    mock_utt = MagicMock()
    mock_utt.kind = "seed"
    mock_utt.speaker_id = "alice"
    mock_utt.text = "Hi"
    mock_utt.audio.url = "/tmp/audio.mp3"
    mock_utt.timing.t_start_ms = 0
    mock_utt.timing.t_end_ms = 1000
    
    view = MagicMock()
    view.utterances = [mock_utt]
    resolver.get_transcript_view.return_value = view
    
    # Init Conductor
    c = Conductor(writer, metrics, resolver)
    c.room = mock_room
    c.session_id = "s1"
    c.branch_id = "b1"
    # actually import ConductorState
    from app.livekit.conductor import ConductorState
    c.state = ConductorState.PLAYING_SEED
    
    # Mock transition to prevent side effects (live loop)
    c.transition_to = AsyncMock()
    
    # Run seed playback (single step)
    # We patch asyncio.sleep to avoid waiting
    with patch("asyncio.sleep", AsyncMock()):
        await c._run_seed_playback()
    
    # Verify publish_data call
    publish_call = mock_room.local_participant.publish_data.call_args
    data_bytes = publish_call[0][0] # First arg
    payload_str = data_bytes.decode("utf-8")
    packet = AgentPacket(**json.loads(payload_str))
    
    assert packet.type == MsgType.SPEAK_CMD
    cmd = SpeakCmdPayload(**packet.payload)
    assert cmd.audio_url == "/tmp/audio.mp3"
