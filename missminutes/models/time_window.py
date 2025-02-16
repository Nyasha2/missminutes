from dataclasses import dataclass
from datetime import time
from enum import Enum
from typing import List


class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass
class TimeWindow:
    """Represents a time window when tasks can be scheduled."""

    day: DayOfWeek
    start_time: time
    end_time: time

    def __post_init__(self):
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time")


@dataclass
class WeeklySchedule:
    """Represents the weekly schedule of available time windows."""

    time_windows: List[TimeWindow]

    def add_window(self, window: TimeWindow):
        """Add a new time window to the schedule."""
        self.time_windows.append(window)

    def get_windows_for_day(self, day: DayOfWeek) -> List[TimeWindow]:
        """Get all time windows for a specific day."""
        return [w for w in self.time_windows if w.day == day]
