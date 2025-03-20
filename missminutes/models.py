from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field
import uuid
from enum import Enum
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU

class DayOfWeek(Enum):
    """Days of the week"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

class RecurrencePattern(Enum):
    """Types of task recurrence"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"  # For more complex patterns

class DependencyType(Enum):
    """Types of task dependencies"""
    BEFORE = "before"  # This task must be completed before the dependent
    AFTER = "after"    # This task must be completed after the dependent
    DURING = "during"  # This task is a subtask of the dependent
    CONTAINS = "contains"  # This task is a parent task of the dependent
    CONCURRENT = "concurrent"  # This task runs concurrently with the dependent 

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

@dataclass
class Task:
    """A task that needs to be scheduled"""
    # Basic info
    title: str
    description: Optional[str] = None
    duration: timedelta = field(default_factory=lambda: timedelta(hours=1))
    due: Optional[datetime] = None
    
    # Organization
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    subtask_ids: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    
    # Scheduling constraints
    time_profiles: set[tuple[str, str]] = field(default_factory=set)  # set of time profile references (name, id)
    dependencies: dict[str, DependencyType] = field(default_factory=dict)  # Task ID -> dependency type
    dependents: dict[str, DependencyType] = field(default_factory=dict)    # Task ID -> dependency type
    min_session_length: Optional[timedelta] = None
    max_session_length: Optional[timedelta] = None
    buffer_before: timedelta = field(default_factory=lambda: timedelta(minutes=0))
    buffer_after: timedelta = field(default_factory=lambda: timedelta(minutes=0))
    fixed_schedule: bool = False  # If True, must be scheduled exactly as specified
    
    # Progress tracking
    completed: bool = False
    completed_at: Optional[datetime] = None
    time_spent: timedelta = field(default_factory=lambda: timedelta())
    sessions: list[str] = field(default_factory=list)  # Session IDs
    
    def add_dependency(self, dependency: 'Task', dep_type: DependencyType = DependencyType.BEFORE):
        """Add a dependency relationship with specified type"""
        self.dependencies[dependency.id] = dep_type
        # Add inverse relationship to the dependency
        match dep_type:
            case DependencyType.BEFORE:
                inverse_type = DependencyType.AFTER
            case DependencyType.AFTER:
                inverse_type = DependencyType.BEFORE
            case DependencyType.DURING:
                inverse_type = DependencyType.CONTAINS
            case DependencyType.CONTAINS:
                inverse_type = DependencyType.DURING
            case DependencyType.CONCURRENT:
                inverse_type = DependencyType.CONCURRENT
        dependency.dependents[self.id] = inverse_type

    def add_subtask(self, subtask: 'Task'):
        """Add a subtask and update relationships"""
        self.subtask_ids.add(subtask.id)
        subtask.parent_id = self.id
        # Also add as a DURING dependency
        self.add_dependency(subtask, DependencyType.DURING)

    def assign_time_profile(self, profile_ref: tuple[str, str]):
        """Assign a time profile to this task"""
        if profile_ref not in self.time_profiles:
            self.time_profiles.append(profile_ref)

    def remove_time_profile(self, profile_ref: tuple[str, str]):
        """Remove a time profile from this task"""
        if profile_ref in self.time_profiles:
            self.time_profiles.remove(profile_ref)

    def get_remaining_duration(self) -> timedelta:
        """Get remaining duration accounting for time spent"""
        return max(self.duration - self.time_spent, timedelta())

    def add_session(self, session_id: str):
        """Add a session ID to this task"""
        self.sessions.append(session_id)

    def mark_complete(self, completion_time: Optional[datetime] = None):
        """Mark task as complete"""
        self.completed = True
        self.completed_at = completion_time or datetime.now()

    def update_time_spent(self, additional_time: timedelta):
        """Update total time spent on task"""
        self.time_spent += additional_time

    @property
    def total_duration(self) -> timedelta:
        """Get total duration including buffers"""
        return self.duration + self.buffer_before + self.buffer_after

@dataclass
class RecurringTask(Task):
    """A task that recurs according to a schedule"""
    # Recurrence specific fields
    recurrence_pattern: Optional[RecurrencePattern] = None
    recurrence_config: list[str, Any] = field(default_factory=dict)
    recurrence_rule: Optional[rrule] = None  # dateutil rrule for recurrence
    recurrence_start: Optional[datetime] = None  # When recurrence starts
    recurrence_until: Optional[datetime] = None  # When recurrence ends
    recurrence_count: Optional[int] = None  # Number of occurrences
    
    def set_recurrence(self, pattern: RecurrencePattern, 
                       start: datetime, 
                       until: Optional[datetime] = None,
                       count: Optional[int] = None,
                       interval: int = 1,
                       byweekday: Optional[list[int]] = None,
                       bymonthday: Optional[list[int]] = None,
                       bymonth: Optional[list[int]] = None) -> None:
        """
        Set up task recurrence using dateutil's rrule
        
        Args:
            pattern: The recurrence pattern type
            start: Start date for recurrence
            until: End date for recurrence (optional)
            count: Number of occurrences (optional)
            interval: Interval between occurrences (default: 1)
            byweekday: list of weekdays (0=MO, 1=TU, etc.) for weekly recurrence
            bymonthday: list of days of month for monthly recurrence
            bymonth: list of months for yearly recurrence
        """
        self.recurrence_pattern = pattern
        self.recurrence_start = start
        self.recurrence_until = until
        self.recurrence_count = count
        
        # Create the appropriate rrule based on pattern
        freq = None
        if pattern == RecurrencePattern.DAILY:
            freq = DAILY
        elif pattern == RecurrencePattern.WEEKLY:
            freq = WEEKLY
        elif pattern == RecurrencePattern.MONTHLY:
            freq = MONTHLY
        elif pattern == RecurrencePattern.YEARLY:
            freq = YEARLY
        
        # Convert weekday integers to dateutil constants if provided
        weekday_map = {0: MO, 1: TU, 2: WE, 3: TH, 4: FR, 5: SA, 6: SU}
        weekdays = None
        if byweekday:
            weekdays = [weekday_map.get(day) for day in byweekday if day in weekday_map]
        
        # Build rrule kwargs
        kwargs = {
            'freq': freq,
            'dtstart': start,
            'interval': interval
        }
        
        if until:
            kwargs['until'] = until
        if count:
            kwargs['count'] = count
        if weekdays:
            kwargs['byweekday'] = weekdays
        if bymonthday:
            kwargs['bymonthday'] = bymonthday
        if bymonth:
            kwargs['bymonth'] = bymonth
            
        # Store configuration
        self.recurrence_config = {
            'pattern': pattern.value,
            'interval': interval,
            'byweekday': byweekday,
            'bymonthday': bymonthday,
            'bymonth': bymonth
        }
        
        # Create the rrule
        if freq is not None:
            self.recurrence_rule = rrule(**kwargs)
    
    def get_next_occurrences(self, count: int = 5, after: Optional[datetime] = None) -> list[datetime]:
        """
        Get the next occurrences of this task based on its recurrence rule
        
        Args:
            count: Number of occurrences to return
            after: Start looking for occurrences after this datetime (defaults to now)
            
        Returns:
            list of upcoming occurrence datetimes
        """
        if not self.recurrence_rule:
            return []
            
        after = after or datetime.now()
        
        # Handle case where we're starting before the recurrence start
        if after < self.recurrence_start:
            # Include the first occurrence if it's in the future
            return list(self.recurrence_rule.replace(count=count))
            
        # Otherwise find the next occurrences after the specified time
        return list(self.recurrence_rule.replace(dtstart=after, count=count))
        
    @classmethod
    def from_task(cls, task: Task, **recurrence_kwargs) -> 'RecurringTask':
        """
        Create a RecurringTask from an existing Task
        
        Args:
            task: The existing Task to convert
            **recurrence_kwargs: Recurrence parameters to pass to set_recurrence
            
        Returns:
            A new RecurringTask instance with all the original task's properties
        """
        # Create a new RecurringTask with the original task's fields
        recurring_task = cls(
            title=task.title,
            description=task.description,
            duration=task.duration,
            due=task.due,
            id=task.id,  # Keep the same ID
            parent_id=task.parent_id,
            subtask_ids=task.subtask_ids.copy(),
            tags=task.tags.copy(),
            time_profiles=task.time_profiles.copy(),
            dependencies=task.dependencies.copy(),
            dependents=task.dependents.copy(),
            min_session_length=task.min_session_length,
            max_session_length=task.max_session_length,
            buffer_before=task.buffer_before,
            buffer_after=task.buffer_after,
            fixed_schedule=task.fixed_schedule,
            completed=task.completed,
            completed_at=task.completed_at,
            time_spent=task.time_spent,
            sessions=task.sessions.copy()
        )
        
        # Set up recurrence if parameters were provided
        if recurrence_kwargs:
            recurring_task.set_recurrence(**recurrence_kwargs)
            
        return recurring_task

@dataclass
class Session:
    """A scheduled time block for a task"""
    task_id: str
    session_id: str
    start_time: datetime
    end_time: datetime
    completed: bool = False
    time_taken: Optional[timedelta] = None

    @property
    def duration(self) -> timedelta:
        """Get planned duration of session"""
        return self.end_time - self.start_time

    def mark_complete(self, time_taken: Optional[timedelta] = None):
        """Mark session as complete with optional actual time taken"""
        self.completed = True
        self.time_taken = time_taken or self.duration 