from datetime import timedelta
import re
from typing import Union


class DurationParser:
    """Handles flexible parsing of duration inputs"""

    # Patterns for different duration formats
    HOUR_ONLY = re.compile(r"^(\d*\.?\d+)\s*(?:h(?:ours?|rs?)?)?$")
    MINUTE_ONLY = re.compile(r"^(\d+)\s*m(?:ins?|inutes?)?$")
    COMBINED = re.compile(r"^(?:(\d+)\s*h(?:rs?)?)?\s*(?:(\d+)\s*m(?:ins?)?)?$")

    def parse(self, input_str: str) -> timedelta:
        """
        Parse duration string with flexible formats.

        Supported formats:
        - Hours only:
            - "2.5" (assumes hours)
            - "2.5h"
            - "2.5hr"
            - "2.5hrs"
            - "2.5 hours"
        - Minutes only:
            - "30m"
            - "30min"
            - "30mins"
            - "30 minutes"
        - Combined:
            - "1h30m"
            - "1hr30min"
            - "1 hour 30 minutes"

        Returns: timedelta object
        Raises: ValueError if input cannot be parsed
        """
        input_str = input_str.strip().lower()

        # Try combined format first
        combined_match = self.COMBINED.match(input_str)
        if combined_match and (combined_match.group(1) or combined_match.group(2)):
            hours = float(combined_match.group(1) or 0)
            minutes = float(combined_match.group(2) or 0)
            return timedelta(hours=hours, minutes=minutes)

        # Try hours-only format
        hour_match = self.HOUR_ONLY.match(input_str)
        if hour_match:
            hours = float(hour_match.group(1))
            return timedelta(hours=hours)

        # Try minutes-only format
        minute_match = self.MINUTE_ONLY.match(input_str)
        if minute_match:
            minutes = float(minute_match.group(1))
            return timedelta(minutes=minutes)

        raise ValueError(
            "Invalid duration format. Examples:\n"
            "- '2.5' or '2.5h' (2.5 hours)\n"
            "- '30m' or '30min' (30 minutes)\n"
            "- '1h30m' (1 hour 30 minutes)"
        )

    def format(self, duration: Union[timedelta, float]) -> str:
        """Format a duration (timedelta or hours) into a human-readable string"""
        if isinstance(duration, float):
            duration = timedelta(hours=duration)

        total_minutes = duration.total_seconds() / 60
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)

        if hours and minutes:
            return f"{hours}h{minutes}m"
        elif hours:
            return f"{hours}h"
        else:
            return f"{minutes}m"
