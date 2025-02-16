from datetime import datetime
from typing import List

from ..models.time_window import TimeWindow, WeeklySchedule, DayOfWeek
from ..storage.json_store import JsonStore

class TimeWindowService:
    """Service layer for managing time windows."""

    def __init__(self, store: JsonStore):
        self.store = store

    def add_window(self, day: str, start_time: str, end_time: str) -> TimeWindow:
        """Add a new time window."""
        try:
            day_enum = DayOfWeek[day.upper()]
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()

            window = TimeWindow(day=day_enum, start_time=start, end_time=end)

            schedule = self.store.load_schedule()
            schedule.add_window(window)
            self.store.save_schedule(schedule)

            return window

        except (ValueError, KeyError) as e:
            raise TimeWindowError(f"Invalid window parameters: {str(e)}")

    def get_all_windows(self) -> List[TimeWindow]:
        """Get all time windows."""
        schedule = self.store.load_schedule()
        return schedule.time_windows


class TimeWindowError(Exception):
    """Raised when there's an error managing time windows."""

    pass
