from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid


@dataclass
class Task:
    """Represents a task in the system."""

    title: str
    duration: timedelta
    due_date: datetime
    completed: bool = False
    id: str = None  # UUID string

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

    def mark_complete(self):
        """Mark the task as completed."""
        self.completed = True

    def mark_incomplete(self):
        """Mark the task as not completed."""
        self.completed = False

    def is_due_soon(self, threshold_days: int = 1) -> bool:
        """Check if the task is due within the specified threshold."""
        if self.completed:
            return False
        time_until_due = self.due_date - datetime.now()
        return time_until_due.days <= threshold_days
