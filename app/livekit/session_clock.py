import time
from enum import Enum
from typing import Optional


class ClockState(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"


class SessionClock:
    """
    A session-time clock that:
    - Excludes paused durations from elapsed time
    - Can jump backward on rewind
    
    Formula:
        session_time = (wall_now - wall_start - total_paused) + session_time_offset
    """
    
    def __init__(self):
        self._wall_start: Optional[float] = None
        self._total_paused_wall_ms: float = 0.0
        self._pause_wall_started_at: Optional[float] = None
        self._session_time_offset_ms: float = 0.0
        self._state: ClockState = ClockState.PAUSED
    
    def start(self) -> None:
        """Start the clock. Should be called once at session start."""
        self._wall_start = time.time() * 1000  # Convert to ms
        self._total_paused_wall_ms = 0.0
        self._pause_wall_started_at = None
        self._session_time_offset_ms = 0.0
        self._state = ClockState.RUNNING
    
    def now_ms(self) -> float:
        """Get current session time in milliseconds."""
        if self._wall_start is None:
            return 0.0
        
        wall_now = time.time() * 1000
        
        # If paused, use the pause start time as "now"
        if self._state == ClockState.PAUSED and self._pause_wall_started_at is not None:
            wall_now = self._pause_wall_started_at
        
        elapsed = wall_now - self._wall_start - self._total_paused_wall_ms
        return max(0.0, elapsed + self._session_time_offset_ms)
    
    def pause(self) -> float:
        """
        Pause the clock. Returns current session time.
        """
        if self._state == ClockState.PAUSED:
            return self.now_ms()
        
        self._pause_wall_started_at = time.time() * 1000
        self._state = ClockState.PAUSED
        return self.now_ms()
    
    def resume(self) -> float:
        """
        Resume the clock. Returns current session time.
        """
        if self._state == ClockState.RUNNING:
            return self.now_ms()
        
        if self._pause_wall_started_at is not None:
            pause_duration = (time.time() * 1000) - self._pause_wall_started_at
            self._total_paused_wall_ms += pause_duration
            self._pause_wall_started_at = None
        
        self._state = ClockState.RUNNING
        return self.now_ms()
    
    def rewind_to(self, target_ms: float) -> float:
        """
        Jump session time backward to target_ms.
        Clock remains in current state (paused or running).
        Returns the new session time.
        """
        current = self.now_ms()
        delta = target_ms - current
        self._session_time_offset_ms += delta
        return self.now_ms()
    
    @property
    def state(self) -> ClockState:
        return self._state
    
    @property
    def is_paused(self) -> bool:
        return self._state == ClockState.PAUSED
    
    def to_sync_payload(self) -> dict:
        """Return payload for CLOCK_SYNC event."""
        return {
            "session_time_ms": self.now_ms(),
            "is_paused": self.is_paused,
            "state": self._state.value
        }
