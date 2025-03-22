from .tasks import Task, RecurringTask, Session
from .timeprofile import TimeProfile
from .timedomain import TimeDomain, TimeSlot 
from .events import Event, RecurringEvent
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid
import copy

@dataclass
class Scheduler:
    """Task scheduler that uses time domain projections"""
    tasks: dict[str, Task] = field(default_factory=dict)
    time_profiles: dict[str, TimeProfile] = field(default_factory=dict)
    scheduled_sessions: list[Session] = field(default_factory=list)
    events: dict[str, Event] = field(default_factory=dict)
    start_date: datetime = field(default_factory=datetime.now)
    days: int = field(default=7)
    
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
    
    def _schedule_task(self, task: Task) -> None:
        """Schedule a single task"""
        # Get the task's remaining duration
        task_duration = task.get_remaining_duration()
        
        # Project time map for this task, passing the scheduler for event dependencies
        task_time_domain = task.project_time_domain(self.start_date, self.days)
        
        # Find available slots considering already scheduled sessions and events
        available_time_domain = self.apply_scheduled_constraints(task_time_domain, self.start_date, self.start_date + timedelta(days=self.days))
        
        # Determine minimum session length for this task
        min_session_length = task.min_session_length or task_duration
        
        # Get slots that are long enough for at least the minimum session length
        suitable_slots = available_time_domain.get_available_slots(min_session_length)
        
        if suitable_slots:
            # Sort slots by start time
            sorted_slots = sorted(suitable_slots, key=lambda s: s.start)
            
            # Track remaining duration to schedule
            remaining_duration = task_duration
            
            while remaining_duration > timedelta() and sorted_slots:
                # Choose the earliest available slot
                best_slot = sorted_slots[0]
                
                # Determine session length for this slot
                if task.max_session_length:
                    # Limit by max session length if specified
                    session_length = min(
                        remaining_duration,
                        task.max_session_length,
                        best_slot.duration
                    )
                else:
                    # Otherwise use as much of the slot as needed
                    session_length = min(remaining_duration, best_slot.duration)
                
                # Create a session
                session = Session(
                    task_id=task.id,
                    session_id=str(uuid.uuid4()),
                    start_time=best_slot.start,
                    end_time=best_slot.start + session_length,
                    completed=False
                )
                
                # Add to scheduled sessions
                self.scheduled_sessions.append(session)
                
                # Add session to task
                task.add_session(session.session_id)
                
                # Update remaining duration
                remaining_duration -= session_length
                
                # Create a time domain with the current slots
                current_domain = TimeDomain(time_slots=[s for s in sorted_slots])
                
                # Apply scheduled constraints to get available slots
                available_domain = self.apply_scheduled_constraints(current_domain, self.start_date, self.start_date + timedelta(days=self.days))
                
                # Add a mandatory break between sessions of the same task
                # by creating a buffer slot around the just scheduled session
                if task.max_session_length:
                    buffer_slot = TimeSlot(
                        session.start_time - timedelta(minutes=30),  # 30 min buffer before
                        session.end_time + timedelta(minutes=30)     # 30 min buffer after
                    )
                    
                    # Remove this buffer from available slots to prevent back-to-back sessions
                    available_domain.subtract_slot(buffer_slot)
                
                    # Get suitable slots and sort them
                    sorted_slots = available_domain.get_available_slots(min_session_length)
                    sorted_slots = sorted(sorted_slots, key=lambda s: s.start)
                else:
                    self.handle_scheduling_conflict(task)
                

    def schedule(self, start_date: datetime = None, days: int = None) -> list[Session]:
        """Schedule all tasks within the given time period"""
        # Sort tasks by priority (due date, dependencies, etc.)
        # Skip completed tasks
        if start_date:
            self.start_date = start_date
        if days:
            self.days = days
            
        uncompleted_tasks = [t for t in self.tasks.values() if not t.completed]
        sorted_task_ids = self.sort_tasks_by_priority(uncompleted_tasks)
        
        # For each task, project its time map and find suitable slots
        for task_id in sorted_task_ids:
            task = self.tasks[task_id]
            self._schedule_task(task)
        return self.scheduled_sessions
    
    def sort_tasks_by_priority(self, tasks: list[Task]) -> list[str]:
        """
        Sort tasks by priority (due date, dependencies, etc.)
        Returns a list of task IDs in priority order
        """
               
        # Sort criteria:
        # 1. Fixed schedule tasks first
        # 2. Then by due date (earlier = higher priority)
        # 3. Then by dependency count (more dependencies = higher priority)
        # 4. Finally by ID for stable sorting
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                not t.fixed_schedule,  # Fixed schedule first
                t.due or datetime.max,  # Earlier due date
                -len(t.dependencies),   # More dependencies
                t.id                    # Stable sorting
            )
        )
        return [t.id for t in sorted_tasks]
    
    def get_events(self, start_date: datetime, end_date: datetime) -> list[Event]:
        """Get all events within a date range"""
        return [e for e in self.events.values() if e.start_time <= end_date and e.end_time >= start_date]
    
    def apply_scheduled_constraints(self, time_domain: TimeDomain, start_date: datetime, end_date: datetime) -> TimeDomain:
        """Apply constraints from already scheduled sessions and events"""
        result = copy.deepcopy(time_domain)
        
        # Create a TimeDomain representing all scheduled sessions
        scheduled_domain = TimeDomain()
        
        # Add sessions to scheduled domain
        for session in self.scheduled_sessions:
            scheduled_domain.add_slot(session.start_time, session.end_time)
        
        # Add events to scheduled domain
        events_in_range = self.get_events(start_date, end_date)
        for event in events_in_range:
            scheduled_domain.add_slot(event.start_time, event.end_time)
        
        # Subtract scheduled sessions and events from the available time
        return result.subtract(scheduled_domain)
    
    def handle_scheduling_conflict(self, task: Task) -> None:
        """Handle case where a task couldn't be scheduled"""
        # For now, just log the conflict
        # In a real implementation, you might want to:
        # - Relax some constraints
        # - Notify the user
        # - Try alternative scheduling strategies
        print(f"Scheduling conflict: Could not schedule task '{task.title}' (id: {task.id})")

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