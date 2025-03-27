from datetime import datetime, timedelta
from dataclasses import dataclass, field
import copy
from typing import Optional, Callable
from portion import closed, IntervalDict
from .timeprofile import DayOfWeek, TimeProfile

@dataclass
class TimeDomain:
    """A collection of available time slots within a scheduling period"""
    time_slots: IntervalDict = field(default_factory=IntervalDict)
    
    def add_slot(self, start: datetime, end: datetime, weight: int = 1) -> None:
        """Add a time slot to the map"""
        self.time_slots[closed(start, end)] = weight
    
    def remove_slot(self, start: datetime, end: datetime) -> None:
        """Remove a specific slot from the map"""
        self.time_slots.pop(closed(start, end), None)
    
    @classmethod
    def from_time_profile(cls, profile: TimeProfile, start_date: datetime, 
                         days: int = 7) -> 'TimeDomain':
        """Create a TimeMap from a TimeProfile for a specific period"""
        time_domain = cls()
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            day_of_week = DayOfWeek(current_date.weekday())
            
            # Get the day schedule from the profile
            day_schedule = profile.day_schedules[day_of_week]
            
            # Add each time window as a slot
            for window in day_schedule.time_windows:
                slot_start = current_date.replace(
                    hour=window.start_hour, 
                    minute=window.start_minute,
                    second=0, microsecond=0
                )
                slot_end = current_date.replace(
                    hour=window.end_hour,
                    minute=window.end_minute,
                    second=0, microsecond=0
                )
                time_domain.add_slot(slot_start, slot_end)
        
        return time_domain

    def add(self, other: 'TimeDomain') -> 'TimeDomain':
        """Add another TimeDomain to this one (this + other)"""
        result = self.time_slots.combine(other.time_slots, lambda a, b: a + b)
        return TimeDomain(result)

    def subtract(self, other: 'TimeDomain') -> None:
        """Subtract another TimeDomain from this one (this - other). Returns 
        this TimeDomain with the intersecting values for intersecting intervals 
        subtracted"""        
        result = self.time_slots.combine(other.time_slots, lambda a, b: a - b)
        result = result[self.time_slots.domain()] 
        return TimeDomain(result)
    
    def combine(self, other: 'TimeDomain', how: Callable[[int, int], int]) -> 'TimeDomain':
        """Combine two TimeDomains using a custom function to combine data values"""
        result = self.time_slots.combine(other.time_slots, how)
        return TimeDomain(result)
    
    def trim_left(self, point: datetime) -> None:
        """Trim all intervals to the left of point"""
        domain_upper = self.time_slots.domain().upper
        self.time_slots = self.time_slots[closed(point, domain_upper)]
    
    def trim_right(self, point: datetime) -> None:
        """Trim all intervals to the right of point"""
        domain_lower = self.time_slots.domain().lower
        self.time_slots = self.time_slots[closed(domain_lower, point)]
    
    # set like operations
    def difference(self, other: 'TimeDomain') -> 'TimeDomain':
        """Return the difference between this TimeDomain and another (this - other). Returns 
        a new TimeDomain with intervals in this that are not in other, data values of this
        unchanged."""
        result = self.time_slots[self.time_slots.domain() - other.time_slots.domain()] 
        return TimeDomain(result)
    
    def intersection(self, other: 'TimeDomain') -> 'TimeDomain':
        """Return the intersection of this TimeDomain and another (this & other). Returns 
        a new TimeDomain with intervals in both this and other, data values of this
        unchanged."""
        result = self.time_slots[other.time_slots.domain()]
        return TimeDomain(result)
    
    def union(self, other: 'TimeDomain') -> 'TimeDomain':
        """Return the union of this TimeDomain and another (this | other). Returns 
        a new TimeDomain with intervals in either this or other, data values of this
        unchanged."""
        result = self.time_slots.combine(other.time_slots, lambda a, _: a)
        return TimeDomain(result)

    def total_time(self) -> timedelta:
        """Calculate the total available time in this map"""
        total = timedelta()
        for iv in self.time_slots:
            for atomic in iv:
                total += atomic.upper - atomic.lower
        return total
    
    def total_weight(self) -> int:
        """Calculate the total weight of all intervals in this map"""
        total = 0
        for iv, value in self.time_slots.items():
            total += value * len(iv)
        return total
    
    def total_weight_time(self) -> int:
        """Calculate the total weight time of all intervals in this map"""
        total = 0
        for iv, value in self.time_slots.items():
            for atomic in iv:
                total += value * (atomic.upper - atomic.lower).total_seconds()
        return total

    def copy(self) -> 'TimeDomain':
        """Create a deep copy of the TimeDomain"""
        return copy.deepcopy(self)

    def is_empty(self) -> bool:
        """Check if domain has any viable slots"""
        return len(self.time_slots) == 0
    
    def __str__(self) -> str:
        """Return a string representation of the TimeDomain"""
        if not self.time_slots:
            return "Empty TimeDomain"
        
        slots_str = "\n".join([f"  {slot.lower.strftime('%Y-%m-%d %H:%M')} - {slot.upper.strftime('%Y-%m-%d %H:%M')}" for slot in self.time_slots])
        return f"TimeDomain with {len(self.time_slots)} slots:\n{slots_str}"
    
    def visualize(self, start_date: Optional[datetime] = None, days: int = 7) -> None:
        """
        Generate a calendar-like visualization of the time domain
        
        Args:
            start_date: The start date for visualization (defaults to earliest slot or today)
            days: Number of days to visualize
        """
        if not self.time_slots:
            return "Empty TimeDomain - nothing to visualize"
        
        # Determine start date if not provided
        if start_date is None:
            if self.time_slots:
                # Use the earliest slot date
                start_date = self.time_slots.domain().lower
            else:
                # Default to today
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Ensure start_date has time set to midnight
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Determine the end date
        end_date = start_date + timedelta(days=days)
        
        # Filter slots that fall within our visualization range
        visible_slots = self.time_slots[closed(start_date, end_date)]
        
        if not visible_slots:
            return f"No time slots to visualize between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}"
        
        # Determine the hour range to display (default 8am-8pm if no slots in range)
        min_hour = min((slot.lower.hour for slot in visible_slots), default=8)
        max_hour = max((slot.upper.hour for slot in visible_slots), default=20)
        
        min_hour = max(0, min(min_hour, 0))
        max_hour = min(23, max(max_hour, 23))
        
        # Build the calendar visualization
        result = []
        
        # Add header with dates
        header = "      |"
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            header += f"  {current_date.strftime('%a %m/%d')}  |"
        result.append(header)
        
        # Add separator
        separator = "------+" + "-------------+".rjust(14, '-') * days
        result.append(separator)
        
        # Add rows for each hour
        for hour in range(min_hour, max_hour + 1):
            hour_str = f"{hour:02d}:00 |"
            
            for day_offset in range(days):
                current_date = start_date + timedelta(days=day_offset)
                hour_start = current_date.replace(hour=hour, minute=0)
                hour_end = hour_start + timedelta(hours=1)
                
                has_slot = visible_slots.domain().overlaps(closed(hour_start, hour_end))
                
                if has_slot:
                    hour_str += " ███████████ |"
                else:
                    hour_str += "             |"
            
            result.append(hour_str)
        
        # Add final separator
        result.append(separator)
        
        print("\n".join(result))