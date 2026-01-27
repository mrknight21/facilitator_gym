import pytest
import time
from unittest.mock import patch
from app.livekit.session_clock import SessionClock, ClockState


def test_clock_starts_at_zero():
    clock = SessionClock()
    clock.start()
    # Should be very close to 0 right after start
    assert clock.now_ms() < 100  # Within 100ms


def test_clock_ticks_forward():
    clock = SessionClock()
    clock.start()
    
    time.sleep(0.1)  # 100ms
    
    elapsed = clock.now_ms()
    assert 90 < elapsed < 150  # ~100ms with some tolerance


def test_pause_stops_time():
    clock = SessionClock()
    clock.start()
    
    time.sleep(0.05)  # 50ms
    paused_at = clock.pause()
    
    time.sleep(0.1)  # 100ms while paused
    
    # Time should not have advanced
    assert abs(clock.now_ms() - paused_at) < 5


def test_resume_continues_from_pause():
    clock = SessionClock()
    clock.start()
    
    time.sleep(0.05)  # 50ms
    paused_at = clock.pause()
    
    time.sleep(0.1)  # 100ms while paused (excluded)
    
    clock.resume()
    time.sleep(0.05)  # 50ms after resume
    
    # Should be ~100ms total (50 before pause + 50 after resume)
    # The 100ms pause should be excluded
    elapsed = clock.now_ms()
    assert 90 < elapsed < 130


def test_rewind_jumps_backward():
    clock = SessionClock()
    clock.start()
    
    time.sleep(0.1)  # 100ms
    
    # Rewind to 50ms
    clock.rewind_to(50)
    
    # Should be at ~50ms now
    assert 45 < clock.now_ms() < 60


def test_rewind_while_paused():
    clock = SessionClock()
    clock.start()
    
    time.sleep(0.1)  # 100ms
    clock.pause()
    
    # Rewind to 30ms
    clock.rewind_to(30)
    
    # Should be at 30ms and still paused
    assert 25 < clock.now_ms() < 35
    assert clock.is_paused


def test_clock_state():
    clock = SessionClock()
    assert clock.state == ClockState.PAUSED  # Initial state
    
    clock.start()
    assert clock.state == ClockState.RUNNING
    
    clock.pause()
    assert clock.state == ClockState.PAUSED
    
    clock.resume()
    assert clock.state == ClockState.RUNNING


def test_sync_payload():
    clock = SessionClock()
    clock.start()
    
    payload = clock.to_sync_payload()
    assert "session_time_ms" in payload
    assert "is_paused" in payload
    assert payload["is_paused"] == False
    assert payload["state"] == "running"
