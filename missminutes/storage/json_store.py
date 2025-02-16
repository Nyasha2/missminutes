import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from ..models.task import Task
from ..models.time_window import TimeWindow, WeeklySchedule, DayOfWeek
from ..scheduler.basic_scheduler import ScheduledTask


class JsonStore:
    """Handles persistence of tasks and schedule data using JSON files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.tasks_file = self.data_dir / "tasks.json"
        self.schedule_file = self.data_dir / "schedule.json"
        self.scheduled_tasks_file = self.data_dir / "scheduled_tasks.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Create the data directory if it doesn't exist."""
        self.data_dir.mkdir(exist_ok=True)

    def save_tasks(self, tasks: List[Task]):
        """Save tasks to JSON file."""
        tasks_data = [
            {
                "id": task.id,
                "title": task.title,
                "duration_seconds": task.duration.total_seconds(),
                "due_date": task.due_date.isoformat(),
                "completed": task.completed,
            }
            for task in tasks
        ]

        with open(self.tasks_file, "w") as f:
            json.dump(tasks_data, f, indent=2)

    def load_tasks(self) -> List[Task]:
        """Load tasks from JSON file."""
        if not self.tasks_file.exists():
            return []

        with open(self.tasks_file, "r") as f:
            tasks_data = json.load(f)

        return [
            Task(
                id=task_data["id"],
                title=task_data["title"],
                duration=timedelta(seconds=task_data["duration_seconds"]),
                due_date=datetime.fromisoformat(task_data["due_date"]),
                completed=task_data["completed"],
            )
            for task_data in tasks_data
        ]

    def save_schedule(self, schedule: WeeklySchedule):
        """Save weekly schedule to JSON file."""
        schedule_data = [
            {
                "day": window.day.value,
                "start_time": window.start_time.isoformat(),
                "end_time": window.end_time.isoformat(),
            }
            for window in schedule.time_windows
        ]

        with open(self.schedule_file, "w") as f:
            json.dump(schedule_data, f, indent=2)

    def load_schedule(self) -> WeeklySchedule:
        """Load weekly schedule from JSON file."""
        if not self.schedule_file.exists():
            return WeeklySchedule([])

        with open(self.schedule_file, "r") as f:
            schedule_data = json.load(f)

        time_windows = [
            TimeWindow(
                day=DayOfWeek(window_data["day"]),
                start_time=datetime.strptime(
                    window_data["start_time"], "%H:%M:%S"
                ).time(),
                end_time=datetime.strptime(window_data["end_time"], "%H:%M:%S").time(),
            )
            for window_data in schedule_data
        ]

        return WeeklySchedule(time_windows)

    def save_scheduled_tasks(self, scheduled_tasks: List[ScheduledTask]):
        """Save scheduled tasks to JSON file."""
        scheduled_data = [
            {
                "task_id": st.task.id,
                "start_time": st.start_time.isoformat(),
                "end_time": st.end_time.isoformat(),
            }
            for st in scheduled_tasks
        ]

        with open(self.scheduled_tasks_file, "w") as f:
            json.dump(scheduled_data, f, indent=2)

    def load_scheduled_tasks(self) -> List[ScheduledTask]:
        """Load scheduled tasks from JSON file."""
        if not self.scheduled_tasks_file.exists():
            return []

        # First load all tasks to create a lookup dictionary
        tasks = {task.id: task for task in self.load_tasks()}

        with open(self.scheduled_tasks_file, "r") as f:
            scheduled_data = json.load(f)

        scheduled_tasks = []
        for st_data in scheduled_data:
            task_id = st_data["task_id"]
            if task_id in tasks:
                scheduled_tasks.append(
                    ScheduledTask(
                        task=tasks[task_id],
                        start_time=datetime.fromisoformat(st_data["start_time"]),
                        end_time=datetime.fromisoformat(st_data["end_time"]),
                    )
                )

        return scheduled_tasks
