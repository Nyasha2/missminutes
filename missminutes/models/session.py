from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

@dataclass
class Session:
    """A scheduled time block for a task"""
    task_id: str
    start_time: datetime
    end_time: datetime
    completed: bool = False
    time_taken: Optional[timedelta] = None
    calendar_event_id: Optional[str] = None

    @property
    def duration(self) -> timedelta:
        """Get planned duration of session"""
        return self.end_time - self.start_time

    def mark_complete(self, time_taken: Optional[timedelta] = None):
        """Mark session as complete with optional actual time taken"""
        self.completed = True
        self.time_taken = time_taken or self.duration 