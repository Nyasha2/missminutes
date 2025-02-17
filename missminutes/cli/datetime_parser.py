from datetime import datetime, date, time, timedelta
import re
from typing import Optional, Tuple
from dateutil import parser


class DateTimeParser:
    """Handles flexible parsing of date and time inputs"""

    TIME_ONLY_PATTERN = re.compile(r"^\d{1,2}(?::\d{2})?(?:\s*[ap]m)?$", re.IGNORECASE)
    RELATIVE_PATTERN = re.compile(
        r"^(today|tomorrow|next week)(?:\s+at\s+)?(.+)?$", re.IGNORECASE
    )

    def parse(self, input_str: str) -> datetime:
        """
        Parse date/time string with flexible formats.

        Supported formats:
        - Full datetime: "2024-03-20 14:30" or "3/20/24 2:30pm"
        - Time only: "14:30" or "2:30pm" (assumes today)
        - Relative: "today 2pm", "tomorrow 14:30"

        Returns: datetime object
        Raises: ValueError if input cannot be parsed
        """
        input_str = input_str.strip()

        # Handle time-only input
        if self.TIME_ONLY_PATTERN.match(input_str):
            return self._parse_time_only(input_str)

        # Handle relative dates
        relative_match = self.RELATIVE_PATTERN.match(input_str)
        if relative_match:
            return self._parse_relative(
                relative_match.group(1), relative_match.group(2)
            )

        # Try general parsing for everything else
        try:
            dt = parser.parse(input_str)
            return dt
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Could not parse '{input_str}'. Please use format 'YYYY-MM-DD HH:MM' "
                "or 'HH:MM' for today's date."
            )

    def _parse_time_only(self, time_str: str) -> datetime:
        """Parse time-only input, assuming today's date"""
        try:
            # Parse the time part
            parsed_time = parser.parse(time_str).time()
            # Combine with today's date
            return datetime.combine(date.today(), parsed_time)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid time format: '{time_str}'")

    def _parse_relative(self, rel_str: str, time_str: Optional[str]) -> datetime:
        """Parse relative date references with optional time"""
        base_date = date.today()

        if rel_str.lower() == "tomorrow":
            base_date += timedelta(days=1)
        elif rel_str.lower() == "next week":
            base_date += timedelta(days=7)

        if time_str:
            try:
                parsed_time = parser.parse(time_str).time()
            except (ValueError, TypeError):
                raise ValueError(f"Invalid time format: '{time_str}'")
        else:
            # Default to current time if no time specified
            parsed_time = datetime.now().time()

        return datetime.combine(base_date, parsed_time)
