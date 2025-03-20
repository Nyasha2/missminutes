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
        existing_scheduled_tasks: List[ScheduledTask] = [],
    ) -> List[ScheduledTask]:
        """
        Schedule tasks starting from either now or the next available window, whichever is earlier.
        """
        # Find the next available time window
        next_window_start = None
        current_time = start_datetime

        # Look ahead up to 7 days to find the next window
        for day_offset in range(7):
            check_date = current_time.date() + timedelta(days=day_offset)
            day_of_week = DayOfWeek(check_date.weekday())
            day_windows = self.weekly_schedule.get_windows_for_day(day_of_week)

            for window in day_windows:
                window_start = datetime.combine(check_date, window.start_time)
                if window_start > current_time:
                    next_window_start = window_start
                    break

            if next_window_start:
                break

        if not next_window_start:
            raise SchedulingError("No available time windows found in the next 7 days")

        # Use the earlier of current time or next window start
        effective_start = min(current_time, next_window_start)

        # Sort tasks
        sorted_tasks = sorted(
            [t for t in tasks if not t.completed],
            key=lambda t: (t.due_date),
        )

        scheduled_tasks = []
        current_slot = effective_start

        for task in sorted_tasks:
            scheduled = False

            while not scheduled:
                # Get the current window we're trying to schedule in
                current_date = current_slot.date()
                day_of_week = DayOfWeek(current_date.weekday())
                windows = self.weekly_schedule.get_windows_for_day(day_of_week)

                for window in windows:
                    window_start = datetime.combine(current_date, window.start_time)
                    window_end = datetime.combine(current_date, window.end_time)

                    # Skip if we're before the window
                    if current_slot < window_start:
                        current_slot = window_start

                    # Skip if we're past this window
                    if current_slot >= window_end:
                        continue

                    # Check if task fits in remaining window time
                    remaining_time = window_end - current_slot
                    if remaining_time >= task.duration:
                        # Check for conflicts with existing scheduled tasks
                        task_end = current_slot + task.duration
                        has_conflict = any(
                            (st.start_time < task_end and st.end_time > current_slot)
                            for st in scheduled_tasks + existing_scheduled_tasks
                        )

                        if not has_conflict:
                            scheduled_tasks.append(
                                ScheduledTask(
                                    task=task,
                                    start_time=current_slot,
                                    end_time=task_end,
                                )
                            )
                            current_slot = task_end
                            scheduled = True
                            break
                        else:
                            # Move past the conflicting task
                            conflicting_tasks = [
                                st
                                for st in scheduled_tasks + existing_scheduled_tasks
                                if st.start_time < task_end
                                and st.end_time > current_slot
                            ]
                            current_slot = min(st.end_time for st in conflicting_tasks)
                    else:
                        # Move to next window
                        current_slot = window_end

                if not scheduled:
                    # Move to next day if we couldn't schedule in current day
                    current_slot = datetime.combine(
                        current_date + timedelta(days=1), time(0, 0)
                    )

                    # Check if we've passed the due date
                    # Convert both to date objects for comparison
                    if task.due_date and current_slot.date() > task.due_date.date():
                        raise SchedulingError(
                            f"Unable to schedule task '{task.title}' before its due date"
                        )

        return scheduled_tasks

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
