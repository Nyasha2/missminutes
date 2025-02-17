from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from ..models.task import Task
from ..models.time_window import WeeklySchedule
from ..storage.json_store import JsonStore
from ..scheduler.basic_scheduler import BasicScheduler, ScheduledTask, SchedulingError
from .calendar_service import CalendarService


class TaskService:
    """Service layer for managing tasks and scheduling."""

    def __init__(self):
        self.store = JsonStore()
        self.calendar = CalendarService()
        self._scheduler = None  # Lazy load scheduler

    @property
    def scheduler(self) -> BasicScheduler:
        """Lazy load and cache the scheduler with current schedule."""
        if self._scheduler is None:
            self._scheduler = BasicScheduler(self.store.load_schedule())
        return self._scheduler

    def complete_task(self, task_id):
        """Mark a task as complete and update/remove calendar event"""
        task = self.store.get(task_id)
        if task:
            task.completed = True
            task.completed_at = datetime.now().isoformat()

            self.store.save(task_id, task)
            return True
        return False

    def delete_task(self, task_id):
        """Delete a task and its calendar event"""
        task = self.store.get(task_id)
        if task and task.calendar_event_id:
            self.calendar.delete_event(task.calendar_event_id)
        return self.store.delete(task_id)

    def sync_calendar(self):
        """Force sync between tasks and calendar"""
        events = self.calendar.get_all_events()
        synced = 0

        # Create event_id to task_id mapping
        for event in events:
            if "extendedProperties" in event:
                task_id = event["extendedProperties"]["private"]["task_id"]
                task = self.store.get(task_id)
                if task and not task.calendar_event_id:
                    task.calendar_event_id = event["id"]
                    self.store.save(task_id, task)
                    synced += 1

        return synced

    def add_task(
        self, title: str, duration_hours: float, due_date: datetime
    ) -> Tuple[Task, Optional[str]]:
        """
        Add a new task and attempt to schedule it.
        Returns: (task, error_message)
        error_message is None if scheduling succeeded, otherwise contains the error
        """
        # Create and save task
        task = Task(
            title=title, duration=timedelta(hours=duration_hours), due_date=due_date
        )

        tasks = self.store.load_tasks()
        tasks.append(task)
        self.store.save_tasks(tasks)

        # Attempt to schedule
        scheduling_error = None
        try:
            self._schedule_tasks()
        except TaskSchedulingError as e:
            scheduling_error = str(e)

        return task, scheduling_error

    def update_task(
        self, task_id: str, **updates
    ) -> Tuple[Optional[Task], Optional[str]]:
        """
        Update a task and attempt to reschedule.
        Returns: (updated_task, error_message)
        If task not found, returns (None, error_message)
        """
        tasks = self.store.load_tasks()
        task_to_update = None

        for task in tasks:
            if task.id == task_id:
                task_to_update = task
                # Update task attributes
                for key, value in updates.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                break

        if not task_to_update:
            return None, "Task not found"

        # Save updated task
        self.store.save_tasks(tasks)

        # Attempt to reschedule
        scheduling_error = None
        try:
            self._schedule_tasks()
        except TaskSchedulingError as e:
            scheduling_error = str(e)

        return task_to_update, scheduling_error

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return self.store.load_tasks()

    def get_schedule(self, target_date: datetime) -> List[ScheduledTask]:
        """Get scheduled tasks for a specific date."""
        scheduled_tasks = self.store.load_scheduled_tasks()
        return [
            task
            for task in scheduled_tasks
            if task.start_time.date() == target_date.date()
        ]

    def _schedule_tasks(self):
        """Internal method to schedule all incomplete tasks and sync with calendar."""
        try:
            tasks = self.store.get_all_todo_tasks()
            # Reset scheduler to get fresh schedule
            self._scheduler = None
            scheduled = self.scheduler.schedule_tasks(
                tasks, start_datetime=datetime.now(), existing_scheduled_tasks=[]
            )

            # First, remove any existing calendar events for tasks that are no longer scheduled
            all_tasks = self.store.load_tasks()
            for task in all_tasks:
                if task.calendar_event_id and not any(
                    st.task.id == task.id for st in scheduled
                ):
                    self.calendar.delete_event(task.calendar_event_id)
                    task.calendar_event_id = None

            # Then update/create calendar events only for scheduled tasks
            for scheduled_task in scheduled:
                task = scheduled_task.task
                if task.calendar_event_id:
                    # Update existing event with new scheduled time
                    self.calendar.update_event(
                        task.calendar_event_id,
                        task,
                        scheduled_time=scheduled_task.start_time,
                    )
                else:
                    # Create new event with scheduled time
                    event_id = self.calendar.create_event(
                        task, scheduled_time=scheduled_task.start_time
                    )
                    if event_id:
                        task.calendar_event_id = event_id

            self.store.save_tasks(tasks)
            self.store.save_scheduled_tasks(scheduled)
        except SchedulingError as e:
            raise TaskSchedulingError(str(e))


class TaskSchedulingError(Exception):
    """Raised when there's an error scheduling tasks."""

    pass
