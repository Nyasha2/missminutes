from datetime import datetime, timedelta
from typing import Optional, Any, Union
from dataclasses import dataclass, field
import uuid
from enum import Enum
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU
from .timedomain import TimeDomain
from .timeprofile import TimeProfile
from .events import Event

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

# Forward reference for type checking
Entity = Union['Task', 'Event']  # Either a Task or an Event

@dataclass
class Task:
    """A task that needs to be scheduled"""
    # Basic info
    title: str
    description: Optional[str] = None
    duration: timedelta = field(default_factory=lambda: timedelta(hours=1))
    due: Optional[datetime] = None
    starts_at: Optional[datetime] = None
    
    # Organization
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    subtask_ids: set[str] = field(default_factory=set)
    
    # Scheduling constraints
    time_profiles: list['TimeProfile'] = field(default_factory=list)  # Direct references to TimeProfile objects
    dependencies: dict[str, DependencyType] = field(default_factory=dict)  # Entity ID -> dependency type
    dependents: dict[str, DependencyType] = field(default_factory=dict)    # Entity ID -> dependency type
    min_session_length: Optional[timedelta] = None
    max_session_length: Optional[timedelta] = None
    buffer_before: timedelta = field(default_factory=lambda: timedelta(minutes=0))
    buffer_after: timedelta = field(default_factory=lambda: timedelta(minutes=0))
    fixed_schedule: bool = False  # If True, must be scheduled exactly as specified
    
    # Progress tracking
    completed: bool = False
    completed_at: Optional[datetime] = None
    time_spent: timedelta = field(default_factory=lambda: timedelta())
    sessions: list[str] = field(default_factory=list)
    
    def add_dependency(self, entity: Entity, dep_type: DependencyType = DependencyType.BEFORE):
        """
        Add a dependency relationship with specified type
        
        The entity can be either a Task or an Event
        """
        self.dependencies[entity.id] = dep_type
        
        # Add inverse relationship to the dependency if it's a Task
        # Events don't track dependents
        if hasattr(entity, 'dependents'):
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
            entity.dependents[self.id] = inverse_type

    def add_subtask(self, subtask: 'Task'):
        """Add a subtask and update relationships"""
        self.subtask_ids.add(subtask.id)
        subtask.parent_id = self.id
        # Also add as a DURING dependency
        self.add_dependency(subtask, DependencyType.DURING)

    def assign_time_profile(self, profile: 'TimeProfile'):
        """Assign a time profile to this task"""
        if profile not in self.time_profiles:
            self.time_profiles.append(profile)

    def remove_time_profile(self, profile: 'TimeProfile'):
        """Remove a time profile from this task"""
        if profile in self.time_profiles:
            self.time_profiles.remove(profile)

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

    def project_time_domain(self, start_date: datetime, days: int = 7) -> TimeDomain:
        """Project this task's constraints as a TimeDomain"""
        # Start with all time available
        result = TimeDomain()
        
        # Create a single time slot from start to end date
        period_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = (start_date + timedelta(days=days)).replace(hour=23, minute=59, second=59, microsecond=999999)
                
        domain_start = period_start
        domain_end = period_end
        if self.starts_at and self.starts_at > start_date:
            domain_start = self.starts_at 
        if self.due and self.due < period_end:
            domain_end = self.due
 
        result.add_slot(domain_start, domain_end)
        
        # Apply time profiles if any        
        if self.time_profiles:
            # Get time profiles and apply them as constraints
            for profile in self.time_profiles:
                profile_domain = TimeDomain.from_time_profile(profile, start_date, days)
                result = result.apply_constraint(profile_domain)
        
        # Apply dependency constraints
        # This would be more complex in practice, as you'd need to check each dependency
        # type and how it affects scheduling
        
        # Return the resulting time map with all constraints applied
        return result

@dataclass
class RecurringTask(Task):
    """A task that recurs according to a schedule"""
    # Recurrence specific fields
    recurrence_pattern: Optional[RecurrencePattern] = None
    recurrence_config: dict[str, Any] = field(default_factory=dict)
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
        match pattern:
            case RecurrencePattern.DAILY:
                freq = DAILY
            case RecurrencePattern.WEEKLY:
                freq = WEEKLY
            case RecurrencePattern.MONTHLY:
                freq = MONTHLY
            case RecurrencePattern.YEARLY:
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
    
    def get_occurrences(self, start_date: datetime, count: int) -> list['Task']:
        """
        Get all occurrences of this task within the specified date range
        
        Args:
            start_date: Start date of the period to check for occurrences
            end_date: End date of the period to check for occurrences
            
        Returns:
            list of Task objects representing occurrences within the specified period
        """
        end_date = start_date + timedelta(days=count)
        if not self.recurrence_rule:
            # If no recurrence rule, just return this task if it falls within range
            if self.starts_at and self.starts_at >= start_date and self.starts_at <= end_date:
                return [self]
            return []
            
        # If the recurrence starts after our period ends, there are no occurrences
        if self.recurrence_start > end_date:
            return []
        
        # Determine the start point for finding occurrences
        effective_start = max(start_date, self.recurrence_start)
        
        # Get all occurrence datetimes within the range
        occurrence_dates = list(self.recurrence_rule.between(effective_start, end_date, inc=True))
        
        # Get one extra occurrence beyond the range for due date calculation of the last occurrence
        next_occurrence = None
        if occurrence_dates:
            next_occurrence = self.recurrence_rule.after(end_date, inc=False)
        
        # Create Task objects for each occurrence
        result = []
        for i, occurrence_dt in enumerate(occurrence_dates):
            # Calculate due date based on next occurrence
            if i < len(occurrence_dates) - 1:
                # Due date is the start of the next occurrence
                due_date = occurrence_dates[i + 1]
            elif next_occurrence:
                # For the last occurrence in our range, use the next occurrence beyond the range
                due_date = next_occurrence
            else:
                # Fallback for the very last occurrence in the series
                # Default to end of the day
                due_date = self.recurrence_rule.replace(count=count+1).after(occurrence_dt, inc=False)

            
            # Generate a unique ID for this occurrence
            occurrence_id = str(uuid.uuid4())
            
            # Create a new Task with the same properties but different start time and due date
            occurrence = Task(
                title=self.title,
                description=self.description,
                duration=self.duration,
                due=due_date,
                starts_at=occurrence_dt,
                id=occurrence_id,
                parent_id=self.id,  # Set parent to this recurring task
                time_profiles=self.time_profiles.copy(),
                dependencies=self.dependencies.copy(),
                min_session_length=self.min_session_length,
                max_session_length=self.max_session_length,
                buffer_before=self.buffer_before,
                buffer_after=self.buffer_after,
                fixed_schedule=self.fixed_schedule,
                completed=self.completed
            )
            
            result.append(occurrence)
            
        return result
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
            starts_at=task.starts_at,
            id=task.id,  # Keep the same ID
            parent_id=task.parent_id,
            subtask_ids=task.subtask_ids.copy(),
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