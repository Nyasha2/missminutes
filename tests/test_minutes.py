import unittest
from datetime import datetime, timedelta, date, time
from pathlib import Path
import json
import tempfile
import shutil

from src.models.task import Task
from src.models.time_window import TimeWindow, WeeklySchedule, DayOfWeek
from src.storage.json_store import JsonStore
from src.scheduler.basic_scheduler import BasicScheduler, ScheduledTask, SchedulingError


class TestMinutes(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.store = JsonStore(self.test_dir)

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_task_creation(self):
        """Test task creation and ID generation."""
        task = Task(
            title="Test task",
            duration=timedelta(hours=2),
            due_date=datetime(2024, 3, 20, 17, 0),
        )

        self.assertIsNotNone(task.id)
        self.assertEqual(task.title, "Test task")
        self.assertEqual(task.duration, timedelta(hours=2))
        self.assertFalse(task.completed)

    def test_task_completion(self):
        """Test task completion functionality."""
        task = Task(
            title="Test task",
            duration=timedelta(hours=2),
            due_date=datetime(2024, 3, 20, 17, 0),
        )

        self.assertFalse(task.completed)
        task.mark_complete()
        self.assertTrue(task.completed)
        task.mark_incomplete()
        self.assertFalse(task.completed)

    def test_time_window_validation(self):
        """Test time window creation and validation."""
        # Valid time window
        window = TimeWindow(
            day=DayOfWeek.MONDAY, start_time=time(9, 0), end_time=time(17, 0)
        )
        self.assertEqual(window.day, DayOfWeek.MONDAY)

        # Invalid time window (end before start)
        with self.assertRaises(ValueError):
            TimeWindow(
                day=DayOfWeek.MONDAY, start_time=time(17, 0), end_time=time(9, 0)
            )

    def test_weekly_schedule(self):
        """Test weekly schedule management."""
        schedule = WeeklySchedule([])
        window1 = TimeWindow(
            day=DayOfWeek.MONDAY, start_time=time(9, 0), end_time=time(17, 0)
        )
        window2 = TimeWindow(
            day=DayOfWeek.TUESDAY, start_time=time(10, 0), end_time=time(18, 0)
        )

        schedule.add_window(window1)
        schedule.add_window(window2)

        monday_windows = schedule.get_windows_for_day(DayOfWeek.MONDAY)
        self.assertEqual(len(monday_windows), 1)
        self.assertEqual(monday_windows[0], window1)

    def test_json_storage(self):
        """Test JSON storage functionality."""
        # Create and save a task
        task = Task(
            title="Test task",
            duration=timedelta(hours=2),
            due_date=datetime(2024, 3, 20, 17, 0),
        )
        self.store.save_tasks([task])

        # Load and verify task
        loaded_tasks = self.store.load_tasks()
        self.assertEqual(len(loaded_tasks), 1)
        loaded_task = loaded_tasks[0]
        self.assertEqual(loaded_task.title, task.title)
        self.assertEqual(loaded_task.duration, task.duration)
        self.assertEqual(loaded_task.id, task.id)

    def test_basic_scheduling(self):
        """Test basic scheduling functionality."""
        # Create a schedule with one time window
        window = TimeWindow(
            day=DayOfWeek.MONDAY, start_time=time(9, 0), end_time=time(17, 0)
        )
        schedule = WeeklySchedule([window])
        scheduler = BasicScheduler(schedule)

        # Create two tasks
        task1 = Task(
            title="Task 1",
            duration=timedelta(hours=2),
            due_date=datetime(2024, 3, 20, 17, 0),
        )
        task2 = Task(
            title="Task 2",
            duration=timedelta(hours=3),
            due_date=datetime(2024, 3, 20, 17, 0),
        )

        # Schedule tasks
        scheduled_tasks = scheduler.schedule_tasks(
            [task1, task2],
            start_date=date(2024, 3, 18),  # A Monday
            existing_scheduled_tasks=[],
        )

        self.assertEqual(len(scheduled_tasks), 2)
        # First task should start at 9:00
        self.assertEqual(scheduled_tasks[0].start_time.time(), time(9, 0))
        # Second task should start at 11:00 (after first task)
        self.assertEqual(scheduled_tasks[1].start_time.time(), time(11, 0))

    def test_scheduling_conflicts(self):
        """Test scheduling conflict detection."""
        window = TimeWindow(
            day=DayOfWeek.MONDAY, start_time=time(9, 0), end_time=time(12, 0)
        )
        schedule = WeeklySchedule([window])
        scheduler = BasicScheduler(schedule)

        # Create tasks that won't fit in the window
        task1 = Task(
            title="Long Task",
            duration=timedelta(hours=4),  # Longer than available window
            due_date=datetime(2024, 3, 18, 17, 0),
        )

        # Should raise SchedulingError
        with self.assertRaises(SchedulingError):
            scheduler.schedule_tasks(
                [task1], start_date=date(2024, 3, 18), existing_scheduled_tasks=[]
            )

    def test_due_date_enforcement(self):
        """Test that scheduling respects due dates."""
        window = TimeWindow(
            day=DayOfWeek.MONDAY, start_time=time(9, 0), end_time=time(17, 0)
        )
        schedule = WeeklySchedule([window])
        scheduler = BasicScheduler(schedule)

        # Create a task due before it could possibly be scheduled
        task = Task(
            title="Past Due Task",
            duration=timedelta(hours=2),
            due_date=datetime(2024, 3, 17, 17, 0),  # Due on a Sunday
        )

        # Should raise SchedulingError because due date is before first available slot
        with self.assertRaises(SchedulingError):
            scheduler.schedule_tasks(
                [task],
                start_date=date(2024, 3, 18),  # Monday
                existing_scheduled_tasks=[],
            )


if __name__ == "__main__":
    unittest.main()
