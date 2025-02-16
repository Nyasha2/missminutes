import argparse
from datetime import datetime, timedelta, date
import sys
from typing import List

from ..storage.json_store import JsonStore
from ..models.task import Task
from ..models.time_window import TimeWindow, WeeklySchedule, DayOfWeek
from ..scheduler.basic_scheduler import BasicScheduler, SchedulingError


class CLI:
    def __init__(self):
        self.store = JsonStore()
        self.scheduler = BasicScheduler(self.store.load_schedule())

    def add_task(self, title: str, duration_hours: float, due_date_str: str):
        """Add a new task."""
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M")
            duration = timedelta(hours=duration_hours)

            task = Task(title=title, duration=duration, due_date=due_date)

            # Load existing tasks, add new one, and save
            tasks = self.store.load_tasks()
            tasks.append(task)
            self.store.save_tasks(tasks)

            print(f"Added task: {title}")

            # Try to schedule all tasks
            self._schedule_tasks()

        except ValueError as e:
            print(f"Error: Invalid date format. Use YYYY-MM-DD HH:MM")
            sys.exit(1)

    def list_tasks(self):
        """List all tasks."""
        tasks = self.store.load_tasks()
        if not tasks:
            print("No tasks found.")
            return

        print("\nTasks:")
        print("-" * 60)
        for task in tasks:
            status = "✓" if task.completed else " "
            print(f"[{status}] {task.title}")
            print(f"    Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}")
            print(f"    Duration: {task.duration.total_seconds() / 3600:.1f} hours")
            print(f"    ID: {task.id}")
            print("-" * 60)

    def complete_task(self, task_id: str):
        """Mark a task as complete."""
        tasks = self.store.load_tasks()
        for task in tasks:
            if task.id == task_id:
                task.mark_complete()
                self.store.save_tasks(tasks)
                print(f"Marked task '{task.title}' as complete")

                # Reschedule remaining tasks
                self._schedule_tasks()
                return

        print(f"Error: Task with ID {task_id} not found")

    def show_schedule(self, date_str: str = None):
        """Show scheduled tasks for a specific date."""
        try:
            target_date = (
                datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_str
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
            print(f"    Duration: {st.task.duration.total_seconds() / 3600:.1f} hours")
            print("-" * 60)

    def _schedule_tasks(self):
        """Internal method to schedule all incomplete tasks."""
        try:
            tasks = self.store.load_tasks()
            scheduled = self.scheduler.schedule_tasks(
                tasks, start_date=date.today(), existing_scheduled_tasks=[]
            )
            self.store.save_scheduled_tasks(scheduled)
        except SchedulingError as e:
            print(f"Warning: Scheduling error: {str(e)}")


def main():
    cli = CLI()
    parser = argparse.ArgumentParser(description="Task Scheduler CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add task command
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("title", help="Task title")
    add_parser.add_argument("duration", type=float, help="Duration in hours")
    add_parser.add_argument("due", help="Due date (YYYY-MM-DD HH:MM)")

    # List tasks command
    subparsers.add_parser("list", help="List all tasks")

    # Complete task command
    complete_parser = subparsers.add_parser("complete", help="Mark a task as complete")
    complete_parser.add_argument("task_id", help="Task ID")

    # Show schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Show schedule for a date")
    schedule_parser.add_argument("date", nargs="?", help="Date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.command == "add":
        cli.add_task(args.title, args.duration, args.due)
    elif args.command == "list":
        cli.list_tasks()
    elif args.command == "complete":
        cli.complete_task(args.task_id)
    elif args.command == "schedule":
        cli.show_schedule(args.date)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
