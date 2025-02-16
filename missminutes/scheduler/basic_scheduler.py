from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..models.task import Task
from ..models.time_window import TimeWindow, WeeklySchedule, DayOfWeek


@dataclass
class ScheduledTask:
    """Represents a task that has been scheduled for a specific time."""

    task: Task
    start_time: datetime
    end_time: datetime


class BasicScheduler:
    """A simple scheduler that assigns tasks to available time windows."""

    def __init__(self, weekly_schedule: WeeklySchedule):
        self.weekly_schedule = weekly_schedule

    def schedule_tasks(
        self,
        tasks: List[Task],
        start_datetime: datetime,
        existing_scheduled_tasks: List[ScheduledTask] = None,
    ) -> List[ScheduledTask]:
        """
        Schedule tasks into available time windows starting from the given datetime.
        Takes into account any existing scheduled tasks to avoid conflicts.
        Returns a list of all scheduled tasks (both new and existing).
        """
        existing_scheduled_tasks = existing_scheduled_tasks or []

        # Filter out completed tasks and sort by due date
        pending_tasks = [t for t in tasks if not t.completed]
        pending_tasks.sort(key=lambda t: t.due_date)

        all_scheduled_tasks = existing_scheduled_tasks.copy()
        current_date = start_datetime.date()

        while pending_tasks:
            # Get time windows for the current day
            day_of_week = DayOfWeek(current_date.weekday())
            day_windows = self.weekly_schedule.get_windows_for_day(day_of_week)

            if not day_windows:
                current_date += timedelta(days=1)
                continue

            # Try to schedule tasks in each window of the current day
            tasks_scheduled_today = False
            for window in day_windows:
                # If it's the start date, use start_datetime's time if it's later
                if current_date == start_datetime.date():
                    if start_datetime.time() > window.end_time:
                        # This window has already passed
                        continue
                    window_start_time = max(start_datetime.time(), window.start_time)
                else:
                    window_start_time = window.start_time

                current_time = datetime.combine(current_date, window_start_time)
                window_end = datetime.combine(current_date, window.end_time)

                while pending_tasks and current_time < window_end:
                    task = pending_tasks[0]
                    task_end_time = current_time + task.duration

                    if task_end_time <= window_end:
                        if task_end_time <= task.due_date:
                            all_scheduled_tasks.append(
                                ScheduledTask(
                                    task=task,
                                    start_time=current_time,
                                    end_time=task_end_time,
                                )
                            )
                            pending_tasks.pop(0)
                            tasks_scheduled_today = True
                            current_time = task_end_time
                        else:
                            raise SchedulingError(
                                f"Cannot schedule task '{task.title}' before its due date."
                            )
                    else:
                        break

            if not tasks_scheduled_today and pending_tasks:
                next_day = current_date + timedelta(days=1)
                if any(task.due_date.date() < next_day for task in pending_tasks):
                    raise SchedulingError(
                        "Insufficient time available to schedule all tasks by their due dates"
                    )

            current_date += timedelta(days=1)

        return all_scheduled_tasks

    def get_daily_schedule(
        self, scheduled_tasks: List[ScheduledTask], target_date: date
    ) -> List[ScheduledTask]:
        """Get all scheduled tasks for a specific date."""
        return [
            task for task in scheduled_tasks if task.start_time.date() == target_date
        ]


class SchedulingError(Exception):
    """Raised when tasks cannot be scheduled within their constraints."""

    pass
