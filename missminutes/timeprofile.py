from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

class DayOfWeek(Enum):
    """Days of the week"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
    

@dataclass
class TimeWindow:
    """A specific time window within a day"""
    start_hour: int  # 0-23
    start_minute: int  # 0-59
    end_hour: int  # 0-23
    end_minute: int  # 0-59
    
    def __post_init__(self):
        """Validate time values"""
        if not (0 <= self.start_hour <= 23):
            raise ValueError("Start hour must be between 0 and 23")
        if not (0 <= self.start_minute <= 59):
            raise ValueError("Start minute must be between 0 and 59")
        if not (0 <= self.end_hour <= 23):
            raise ValueError("End hour must be between 0 and 23")
        if not (0 <= self.end_minute <= 59):
            raise ValueError("End minute must be between 0 and 59")
        
        # Check that end time is after start time
        start_time = self.start_hour * 60 + self.start_minute
        end_time = self.end_hour * 60 + self.end_minute
        if end_time <= start_time:
            raise ValueError("End time must be after start time")
    
    def contains_time(self, hour: int, minute: int) -> bool:
        """Check if the given time falls within this window"""
        time_val = hour * 60 + minute
        start_val = self.start_hour * 60 + self.start_minute
        end_val = self.end_hour * 60 + self.end_minute
        return start_val <= time_val < end_val


@dataclass
class DaySchedule:
    """Schedule windows for a specific day"""
    day: DayOfWeek
    time_windows: list[TimeWindow] = field(default_factory=list)
    
    def add_window(self, start_hour: int, start_minute: int, end_hour: int, end_minute: int):
        """Add a time window to this day's schedule"""
        window = TimeWindow(start_hour, start_minute, end_hour, end_minute)
        self.time_windows.append(window)
        return window
    
    def is_available_at(self, hour: int, minute: int) -> bool:
        """Check if any time window contains the given time"""
        return any(window.contains_time(hour, minute) for window in self.time_windows)

@dataclass
class TimeProfile:
    """A named profile containing scheduling preferences for each day of the week"""
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    day_schedules: dict[DayOfWeek, DaySchedule] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize empty day schedules for any missing days"""
        for day in DayOfWeek:
            if day not in self.day_schedules:
                self.day_schedules[day] = DaySchedule(day)
    
    def add_window(self, day: DayOfWeek, start_hour: int, start_minute: int, 
                  end_hour: int, end_minute: int) -> TimeWindow:
        """Add a time window to a specific day"""
        return self.day_schedules[day].add_window(
            start_hour, start_minute, end_hour, end_minute
        )
    
    def add_window_to_days(self, days: list[DayOfWeek], start_hour: int, start_minute: int,
                          end_hour: int, end_minute: int) -> list[TimeWindow]:
        """Add the same time window to multiple days"""
        return [self.add_window(day, start_hour, start_minute, end_hour, end_minute)
                for day in days]
    
    def is_available_at(self, day: DayOfWeek, hour: int, minute: int) -> bool:
        """Check if this profile allows scheduling at the given day and time"""
        return self.day_schedules[day].is_available_at(hour, minute)
    
    def is_datetime_available(self, dt: datetime) -> bool:
        """Check if a specific datetime is available in this profile"""
        day = DayOfWeek(dt.weekday())
        return self.is_available_at(day, dt.hour, dt.minute)
