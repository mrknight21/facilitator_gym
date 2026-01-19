import pytest
import asyncio
import unittest.mock
from unittest.mock import MagicMock, AsyncMock
from app.transcription.worker import TranscriptionWorker
from app.livekit.protocol import MsgType, AgentPacket
from livekit import rtc

@pytest.fixture
def mock_stt():
    stt = MagicMock()
    stt.transcribe = AsyncMock(return_value="Hello World")
    return stt

@pytest.fixture
def mock_room():
    room = MagicMock()
    room.local_participant = MagicMock()
    room.local_participant.publish_data = AsyncMock()
    return room

@pytest.fixture
def worker(mock_stt, mock_room):
    # Patch rtc.Room to return our mock
    with unittest.mock.patch('app.transcription.worker.rtc.Room', return_value=mock_room):
        worker = TranscriptionWorker(mock_stt)
        return worker

@pytest.mark.asyncio
async def test_worker_captures_audio_during_ptt(worker):
    # Simulate valid FAC_START
    participant = MagicMock()
    participant.identity = "user1"
    
    event = MagicMock()
    event.participant = participant
    event.data = json.dumps({
        "type": MsgType.FAC_START,
        "session_id": "test",
        "payload": {}
    }).encode("utf-8")
    
    worker.on_data_received(event)
    assert worker.is_recording == True
    assert worker.current_speaker_id == "user1"
    
    # Simulate Audio Frame
    # Since _handle_audio_stream is async loop, we inspect buffer directly for unit test
    # But we can verify 'start_recording' clears buffer
    worker.audio_capture_buffer.extend(b'\x01\x02')
    
    # Simulate FAC_END
    event_end = MagicMock()
    event_end.participant = participant
    event_end.data = json.dumps({
        "type": MsgType.FAC_END,
        "session_id": "test",
        "payload": {}
    }).encode("utf-8")
    
    # Needs to run the async task spawned by on_data_received
    await worker.stop_recording_and_transcribe()
    
    # Assertions
    assert worker.is_recording == False
    worker.stt_service.transcribe.assert_called_once()
    worker.room.local_participant.publish_data.assert_called_once()
    
    # Check payload of published message
    call_args = worker.room.local_participant.publish_data.call_args
    sent_data = json.loads(call_args[0][0].decode("utf-8"))
    assert sent_data["type"] == "transcript_complete"
    assert sent_data["payload"]["text"] == "Hello World"

import json
