from datetime import datetime, timedelta
from typing import List, Optional, Set, Dict
from dataclasses import dataclass, field
import uuid
from enum import Enum

class RecurrencePattern(Enum):
    """Types of task recurrence"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # For more complex patterns

@dataclass
class TimeWindow:
    """Preferred time window for a task"""
    start_time: datetime
    end_time: datetime
    priority: int = 1  # Higher number = higher priority

@dataclass
class Task:
    """A task that needs to be scheduled"""
    # Basic info
    title: str
    description: Optional[str] = None
    duration: timedelta = field(default_factory=lambda: timedelta(hours=1))
    due_date: Optional[datetime] = None
    
    # Organization
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    subtask_ids: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    
    # Scheduling constraints
    preferred_windows: List[TimeWindow] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)  # Task IDs this task depends on
    dependents: Set[str] = field(default_factory=set)    # Task IDs that depend on this
    min_session_length: Optional[timedelta] = None
    max_session_length: Optional[timedelta] = None
    buffer_before: timedelta = field(default_factory=lambda: timedelta(minutes=0))
    buffer_after: timedelta = field(default_factory=lambda: timedelta(minutes=0))
    fixed_schedule: bool = False  # If True, must be scheduled exactly as specified
    
    # Recurrence
    recurrence_pattern: Optional[RecurrencePattern] = None
    recurrence_config: Dict = field(default_factory=dict)  # Pattern-specific config
    
    # Progress tracking
    completed: bool = False
    completed_at: Optional[datetime] = None
    time_spent: timedelta = field(default_factory=lambda: timedelta())
    sessions: List[str] = field(default_factory=list)  # Session IDs
    
    def add_subtask(self, subtask: 'Task'):
        """Add a subtask and update relationships"""
        self.subtask_ids.add(subtask.id)
        subtask.parent_id = self.id

    def add_dependency(self, dependency: 'Task'):
        """Add a dependency relationship"""
        self.dependencies.add(dependency.id)
        dependency.dependents.add(self.id)

    def add_preferred_window(self, start: datetime, end: datetime, priority: int = 1):
        """Add a preferred time window for scheduling"""
        self.preferred_windows.append(TimeWindow(start, end, priority))
        # Sort by priority
        self.preferred_windows.sort(key=lambda w: w.priority, reverse=True)

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
        if self.time_spent >= self.duration:
            self.mark_complete()

    @property
    def is_fixed_time(self) -> bool:
        """Check if task must be scheduled at exact times"""
        return self.fixed_schedule or bool(self.parent_id)

    @property
    def total_duration(self) -> timedelta:
        """Get total duration including buffers"""
        return self.duration + self.buffer_before + self.buffer_after
