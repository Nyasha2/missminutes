from .tasks import Task, RecurringTask, Session
from .timeprofile import TimeProfile
from .events import Event, RecurringEvent
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from .constraint_solver import ConstraintSolver
from typing import List

@dataclass
class Scheduler:
    """Task scheduler that uses time domain projections"""
    tasks: dict[str, Task] = field(default_factory=dict)
    time_profiles: dict[str, TimeProfile] = field(default_factory=dict)
    scheduled_sessions: list[Session] = field(default_factory=list)
    events: dict[str, Event] = field(default_factory=dict)
    start_date: datetime = field(default_factory=datetime.now)
    days: int = field(default=7)
    solver: ConstraintSolver = field(default_factory=ConstraintSolver)
    
    def add_task(self, task: Task) -> None:
        """Add a task to be scheduled"""
        if task.completed:
            return
        if isinstance(task, RecurringTask):
            occurrences = task.get_occurrences(self.start_date, self.days)
            for occurrence in occurrences:
                self.tasks[occurrence.id] = occurrence
        else:
            self.tasks[task.id] = task
    
    def add_time_profile(self, profile: TimeProfile) -> None:
        """Add a time profile for scheduling"""
        self.time_profiles[profile.id] = profile
    
    def add_event(self, event: Event) -> None:
        """Add an event to the scheduler"""
        if isinstance(event, RecurringEvent):
            occurrences = event.get_occurrences(self.start_date, self.start_date + timedelta(days=self.days))
            for occurrence in occurrences:
                self.events[occurrence.id] = occurrence
        else:
            self.events[event.id] = event

    def schedule(self, start_date: datetime = None, days: int = None) -> list[Session]:
        """Schedule all tasks within the given time period using backtracking"""
        if start_date:
            self.start_date = start_date
        if days:
            self.days = days
        
        uncompleted_tasks = [t for t in self.tasks.values() if not t.completed]    
        events_in_range = self.get_events(self.start_date, self.start_date + timedelta(days=self.days))
        self.scheduled_sessions = self.solver.solve(uncompleted_tasks, events_in_range, self.start_date, self.days)
        
        if not self.scheduled_sessions:
            print("Failed to find a valid schedule")
        
        return self.scheduled_sessions
    
    
    def get_events(self, start_date: datetime, end_date: datetime) -> list[Event]:
        """Get all events within a date range"""
        return [e for e in self.events.values() if e.start_time <= end_date and e.end_time >= start_date]
    


    def print_schedule(self) -> dict:
        """
        Generate a visualization-friendly representation of the schedule
        Returns a dictionary mapping dates to lists of scheduled sessions and events
        """
        schedule_by_day = {}
        
        # Initialize empty lists for each day
        for day_offset in range(self.days):
            current_date = self.start_date + timedelta(days=day_offset)
            date_key = current_date.date().isoformat()
            schedule_by_day[date_key] = []
        
        # Add sessions to their respective days
        for session in self.scheduled_sessions:
            session_date = session.start_time.date().isoformat()
            if session_date in schedule_by_day:
                # Add the session with task info
                task = self.tasks.get(session.task_id)
                if task:
                    schedule_by_day[session_date].append({
                        'type': 'session',
                        'session_id': session.session_id,
                        'task_id': session.task_id,
                        'task_title': task.title,
                        'start_time': session.start_time.isoformat(),
                        'end_time': session.end_time.isoformat(),
                        'duration': str(session.duration),
                        'completed': session.completed
                    })
        
        # Add events to their respective days
        events = self.get_events(self.start_date, self.start_date + timedelta(days=self.days))
        for event in events:
            event_date = event.start_time.date().isoformat()
            if event_date in schedule_by_day:
                schedule_by_day[event_date].append({
                    'type': 'event',
                    'event_id': event.id,
                    'title': event.title,
                    'start_time': event.start_time.isoformat(),
                    'end_time': event.end_time.isoformat(),
                    'duration': str(event.duration),
                    'completed': event.completed,
                })
        
        # Sort each day's items by start time
        for date, items in schedule_by_day.items():
            schedule_by_day[date] = sorted(items, key=lambda x: x['start_time'])
        
        return schedule_by_day 