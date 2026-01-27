import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.livekit.conductor import Conductor, ConductorState
from app.domain.schemas import RewindPlanRes, ReplayUtteranceView, AudioRef, Timing
from app.livekit.protocol import MsgType

@pytest.mark.asyncio
async def test_rewind_full_flow():
    # Setup Mocks
    writer = AsyncMock()
    metrics = MagicMock()
    resolver = AsyncMock()
    rewind_service = AsyncMock()
    replay_event_repo = AsyncMock()
    
    conductor = Conductor(writer, metrics, resolver, rewind_service, replay_event_repo)
    conductor.room = MagicMock()
    conductor.room.connect = AsyncMock()
    conductor.room.local_participant.publish_data = AsyncMock()
    
    # Mock Rewind Plan
    plan = RewindPlanRes(
        new_branch_id="branch-2",
        fork_checkpoint_id="ckpt-1",
        target_utterance_id="utt-1",
        replay_utterances=[
            ReplayUtteranceView(
                utterance_id="utt-2",
                speaker_id="alice",
                kind="ai",
                text="Hello again",
                timing=Timing(),
                audio=AudioRef(url="/tmp/audio.wav"),
                display_id="1"
            )
        ],
        handoff_reason="END_OF_TIMELINE",
        replay_event_id="evt-1"
    )
    rewind_service.create_rewind_plan.return_value = plan
    
    # Mock Resolver to return empty view (fast seed playback)
    view = MagicMock()
    view.utterances = []
    resolver.get_transcript_view.return_value = view
    
    # 1. Start Session
    await conductor.connect("ws://test", "token", "sess-1", "branch-1")
    
    # Wait for Seed Playback to finish and settle in LIVE
    # We can loop until state is LIVE
    for _ in range(10):
        if conductor.state == ConductorState.LIVE:
            break
        await asyncio.sleep(0.01)
        
    assert conductor.state == ConductorState.LIVE
    
    # Mock send_play_asset_cmd BEFORE triggering rewind
    conductor.send_play_asset_cmd = AsyncMock()
    
    # 2. Simulate REWIND_TO command
    payload = {"target_utterance_id": "utt-1", "created_by": "tester"}
    await conductor._handle_rewind_to(payload)
    
    # Verify State Transition
    assert conductor.state == ConductorState.REPLAYING
    assert conductor.branch_id == "branch-2"
    
    # 3. Wait for Replay Loop (Started by transition_to)
    # Give it a moment to start and send command
    await asyncio.sleep(0.1)
    
    # Verify PLAY_ASSET_CMD sent
    conductor.send_play_asset_cmd.assert_called_once()
    args = conductor.send_play_asset_cmd.call_args
    assert args[0][0] == "alice" # speaker
    assert args[0][1] == "/tmp/audio.wav" # audio_url
    
    # 4. Simulate PLAYBACK_DONE
    conductor.playback_done_event.set()
    
    # Wait for loop to finish (loop sleeps 0.5s)
    await asyncio.sleep(0.6)
    
    # Verify ReplayEvent Status Update (Ticket 5.2)
    # Should be called with "replaying" then "completed"
    assert replay_event_repo.update_status.call_count >= 2
    replay_event_repo.update_status.assert_any_call("evt-1", "replaying", first_audio_start_ts=pytest.approx(0, abs=1e10))
    replay_event_repo.update_status.assert_any_call("evt-1", "completed", last_audio_end_ts=pytest.approx(0, abs=1e10))
    
    # Verify Progress Broadcast
    conductor.room.local_participant.publish_data.assert_called()
    
    # Verify NO Cloning (Writer NOT called for replay)
    # Writer might be called for other things, but let's check it wasn't called for "Hello again"
    # Actually, writer is mocked, so we can check calls.
    # It shouldn't be called during replay loop.
    # But wait, we didn't reset mock.
    # Let's just verify it wasn't called with "Hello again"
    for call in writer.append_utterance_and_checkpoint.call_args_list:
        assert call[0][4] != "Hello again"
    
    # Verify Handoff to LIVE
    assert conductor.state == ConductorState.LIVE
    
    # Cleanup
    if conductor.seed_task:
        conductor.seed_task.cancel()
