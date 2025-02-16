from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from ..models.task import Task
from ..models.time_window import WeeklySchedule
from ..storage.json_store import JsonStore
from ..scheduler.basic_scheduler import BasicScheduler, ScheduledTask, SchedulingError


class TaskService:
    """Service layer for managing tasks and scheduling."""

    def __init__(self, store: JsonStore):
        self.store = store
        self._scheduler = None  # Lazy load scheduler

    @property
    def scheduler(self) -> BasicScheduler:
        """Lazy load and cache the scheduler with current schedule."""
        if self._scheduler is None:
            self._scheduler = BasicScheduler(self.store.load_schedule())
        return self._scheduler

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

        # Attempt to schedule - but don't fail if scheduling fails
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

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as complete and reschedule remaining tasks."""
        tasks = self.store.load_tasks()
        completed_task = None

        for task in tasks:
            if task.id == task_id:
                task.mark_complete()
                completed_task = task
                break

        if completed_task:
            self.store.save_tasks(tasks)
            self._schedule_tasks()

        return completed_task

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
        """Internal method to schedule all incomplete tasks."""
        try:
            tasks = self.store.load_tasks()
            # Reset scheduler to get fresh schedule
            self._scheduler = None
            scheduled = self.scheduler.schedule_tasks(
                tasks, start_datetime=datetime.now(), existing_scheduled_tasks=[]
            )
            self.store.save_scheduled_tasks(scheduled)
        except SchedulingError as e:
            raise TaskSchedulingError(str(e))


class TaskSchedulingError(Exception):
    """Raised when there's an error scheduling tasks."""

    pass
