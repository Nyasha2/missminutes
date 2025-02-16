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
        new_tasks: List[Task],
        start_date: date,
        existing_scheduled_tasks: List[ScheduledTask] = None,
    ) -> List[ScheduledTask]:
        """
        Schedule tasks into available time windows starting from the given date.
        Takes into account any existing scheduled tasks to avoid conflicts.
        Returns a list of all scheduled tasks (both new and existing).
        """
        existing_scheduled_tasks = existing_scheduled_tasks or []

        # Filter out completed tasks and sort by due date
        pending_tasks = [t for t in new_tasks if not t.completed]
        pending_tasks.sort(key=lambda t: t.due_date)

        all_scheduled_tasks = existing_scheduled_tasks.copy()
        current_date = start_date

        while pending_tasks:
            # Get time windows for the current day
            day_of_week = DayOfWeek(current_date.weekday())
            day_windows = self.weekly_schedule.get_windows_for_day(day_of_week)

            if not day_windows:
                current_date += timedelta(days=1)
                continue

            # Get existing tasks for this day
            days_scheduled_tasks = [
                st
                for st in existing_scheduled_tasks
                if st.start_time.date() == current_date
            ]

            # Try to schedule tasks in each window of the current day
            tasks_scheduled_today = False
            for window in day_windows:
                current_time = datetime.combine(current_date, window.start_time)
                window_end = datetime.combine(current_date, window.end_time)

                # Try to fit tasks into this window
                while pending_tasks and current_time < window_end:
                    task = pending_tasks[0]
                    task_end_time = current_time + task.duration

                    # Check if task fits in current window
                    if task_end_time <= window_end:
                        # Check for conflicts with existing scheduled tasks
                        conflict = False
                        for scheduled_task in days_scheduled_tasks:
                            if (
                                current_time < scheduled_task.end_time
                                and task_end_time > scheduled_task.start_time
                            ):
                                # Found a conflict, try the next available time
                                current_time = scheduled_task.end_time
                                conflict = True
                                break

                        if conflict:
                            continue

                        # Check if scheduling would meet due date
                        if task_end_time <= task.due_date:
                            new_scheduled_task = ScheduledTask(
                                task=task,
                                start_time=current_time,
                                end_time=task_end_time,
                            )
                            all_scheduled_tasks.append(new_scheduled_task)
                            days_scheduled_tasks.append(new_scheduled_task)
                            pending_tasks.pop(0)
                            tasks_scheduled_today = True
                            current_time = task_end_time
                        else:
                            # Task can't be scheduled to meet its due date
                            raise SchedulingError(
                                f"Cannot schedule task '{task.title}' before its due date"
                            )
                    else:
                        # Task doesn't fit in remaining window time
                        break

            if not tasks_scheduled_today and pending_tasks:
                # If we couldn't schedule any tasks today but still have tasks,
                # check if we're about to miss any due dates
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
