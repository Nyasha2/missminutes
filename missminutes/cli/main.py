import cmd
from datetime import datetime, date, timedelta
from typing import Optional
import shlex

from ..storage.json_store import JsonStore
from ..models.task import Task
from ..models.time_window import DayOfWeek, TimeWindow
from ..scheduler.basic_scheduler import BasicScheduler, SchedulingError
from ..services.task_service import TaskService, TaskSchedulingError
from ..services.window_service import TimeWindowService, TimeWindowError
from .datetime_parser import DateTimeParser
from .duration_parser import DurationParser


class MinutesCUI(cmd.Cmd):
    intro = "Welcome to Miss Minutes CUI. Type help or ? to list commands.\n"
    prompt = "minutes> "

    def __init__(self):
        super().__init__()
        store = JsonStore()
        self.store = store
        self.scheduler = BasicScheduler(self.store.load_schedule())
        self.task_service = TaskService()
        self.window_service = TimeWindowService(store)
        self.datetime_parser = DateTimeParser()
        self.duration_parser = DurationParser()

    def do_add(self, arg):
        """Add a new task. Usage: add "Task title" duration due_date
        Examples:
            add "Write documentation" 2.5h "2024-03-20 17:00"
            add "Team meeting" 1hr "14:30"              # today at 14:30
            add "Quick review" 30m "tomorrow 2pm"       # tomorrow at 14:00
            add "Weekly sync" 1h30m "tomorrow 11:30"    # tomorrow at 11:30
            add "Planning" "2 hours" "next week 10am"   # next week at 10:00
        """
        try:
            parts = shlex.split(arg)
            if len(parts) != 3:
                print("Error: Incorrect number of arguments")
                print('Usage: add "Task title" duration due_date')
                return

            title, duration_str, due_date_str = parts

            # Use flexible duration parsing
            duration = self.duration_parser.parse(duration_str)
            duration_hours = duration.total_seconds() / 3600

            # Use flexible datetime parsing
            due_date = self.datetime_parser.parse(due_date_str)

            task, scheduling_error = self.task_service.add_task(
                title, duration_hours, due_date
            )

            print(f"Added task: {task.title} ({self.duration_parser.format(duration)})")
            if scheduling_error:
                print(
                    f"Warning: Task saved but could not be scheduled: {scheduling_error}"
                )
                print(
                    "You may need to adjust the task parameters or available time windows."
                )

        except ValueError as e:
            print(f"Error: {str(e)}")

    def do_list(self, arg):
        """List all tasks."""
        tasks = self.task_service.get_all_tasks()
        if not tasks:
            print("No tasks found.")
            return

        print("\nTasks:")
        print("-" * 60)
        for task in tasks:
            status = "✓" if task.completed else " "
            print(f"[{status}] {task.title}")
            print(f"    Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}")
            print(f"    Duration: {self.duration_parser.format(task.duration)}")
            print(f"    ID: {task.id}")
            print("-" * 60)

    def do_complete(self, arg):
        """Mark a task as complete. Usage: complete <task_id>"""
        task_id = arg.strip()
        if not task_id:
            print("Error: Task ID required")
            return

        tasks = self.store.load_tasks()
        for task in tasks:
            if task.id == task_id:
                task.mark_complete()
                self.store.save_tasks(tasks)
                print(f"Marked task '{task.title}' as complete")
                self._schedule_tasks()
                return

        print(f"Error: Task with ID {task_id} not found")

    def do_schedule(self, arg):
        """Show schedule for a date. Usage: schedule [YYYY-MM-DD]
        If no date is provided, shows today's schedule."""
        try:
            target_date = (
                datetime.strptime(arg.strip(), "%Y-%m-%d").date()
                if arg.strip()
                else date.today()
            )
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            return

        scheduled_tasks = self.store.load_scheduled_tasks()
        daily_tasks = self.scheduler.get_daily_schedule(scheduled_tasks, target_date)

        if not daily_tasks:
            print(f"No tasks scheduled for {target_date}")
            return

        print(f"\nSchedule for {target_date}:")
        print("-" * 60)
        for st in sorted(daily_tasks, key=lambda x: x.start_time):
            print(
                f"{st.start_time.strftime('%H:%M')} - "
                f"{st.end_time.strftime('%H:%M')}: {st.task.title}"
            )
            print(f"    Duration: {self.duration_parser.format(st.task.duration)}")
            print("-" * 60)

    def do_window(self, arg):
        """Add or list time windows.
        Usage:
            window add <day> <start_time> <end_time>
            window list
        Example: window add monday 09:00 17:00
        """
        parts = arg.strip().split()
        if not parts:
            print("Error: Subcommand required (add/list)")
            return

        if parts[0] == "list":
            schedule = self.store.load_schedule()
            if not schedule.time_windows:
                print("No time windows configured.")
                return

            print("\nTime Windows:")
            print("-" * 60)
            for window in sorted(schedule.time_windows, key=lambda w: w.day.value):
                print(
                    f"{window.day.name}: "
                    f"{window.start_time.strftime('%H:%M')} - "
                    f"{window.end_time.strftime('%H:%M')}"
                )
            print("-" * 60)

        elif parts[0] == "add":
            if len(parts) != 4:
                print("Error: Incorrect number of arguments")
                print("Usage: window add <day> <start_time> <end_time>")
                return

            try:
                _, day_str, start_str, end_str = parts
                day = DayOfWeek[day_str.upper()]
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()

                window = TimeWindow(day=day, start_time=start_time, end_time=end_time)
                schedule = self.store.load_schedule()
                schedule.add_window(window)
                self.store.save_schedule(schedule)

                print(f"Added time window for {day.name}")
                self._schedule_tasks()  # Reschedule tasks with new window

            except (ValueError, KeyError) as e:
                print("Error: Invalid input format")
                print("Usage: window add <day> <start_time> <end_time>")
                print("Example: window add monday 09:00 17:00")

    def do_quit(self, arg):
        """Exit the application."""
        print("Goodbye!")
        return True

    def _schedule_tasks(self):
        """Internal method to schedule all incomplete tasks."""
        try:
            tasks = self.store.load_tasks()
            # Refresh scheduler with latest schedule
            self.scheduler = BasicScheduler(self.store.load_schedule())
            scheduled = self.scheduler.schedule_tasks(
                tasks, start_datetime=datetime.now(), existing_scheduled_tasks=[]
            )
            self.store.save_scheduled_tasks(scheduled)
        except SchedulingError as e:
            print(f"Warning: Scheduling error: {str(e)}")


def main():
    MinutesCUI().cmdloop()


if __name__ == "__main__":
    main()
