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
    
    def remove_time(self, day: DayOfWeek, start_hour: int, start_minute: int, 
                   end_hour: int, end_minute: int) -> None:
        """
        Remove a time window from a specific day's schedule
        
        Args:
            day: Day of week to modify
            start_hour: Start hour (0-23)
            start_minute: Start minute (0-59)
            end_hour: End hour (0-23)
            end_minute: End minute (0-59)
        """
        day_schedule = self.day_schedules[day]
        
        # Create a time value range to compare against
        start_val = start_hour * 60 + start_minute
        end_val = end_hour * 60 + end_minute
        
        # Make a copy of windows to avoid modification during iteration
        windows_to_keep = []
        windows_to_add = []
        
        for window in day_schedule.time_windows:
            window_start = window.start_hour * 60 + window.start_minute
            window_end = window.end_hour * 60 + window.end_minute
            
            # If window doesn't overlap with time to remove, keep it unchanged
            if end_val <= window_start or start_val >= window_end:
                windows_to_keep.append(window)
                continue
                
            # Window overlaps with time to remove, we need to split it
            
            # Part before time to remove
            if window_start < start_val:
                windows_to_add.append(TimeWindow(
                    window.start_hour,
                    window.start_minute,
                    start_hour,
                    start_minute
                ))
                
            # Part after time to remove
            if window_end > end_val:
                windows_to_add.append(TimeWindow(
                    end_hour,
                    end_minute,
                    window.end_hour,
                    window.end_minute
                ))
        
        # Replace windows with the new set
        day_schedule.time_windows = windows_to_keep + windows_to_add
    
    def is_available_at(self, day: DayOfWeek, hour: int, minute: int) -> bool:
        """Check if this profile allows scheduling at the given day and time"""
        return self.day_schedules[day].is_available_at(hour, minute)
    
    def is_datetime_available(self, dt: datetime) -> bool:
        """Check if a specific datetime is available in this profile"""
        day = DayOfWeek(dt.weekday())
        return self.is_available_at(day, dt.hour, dt.minute)
    
