from datetime import datetime, timedelta
from dataclasses import dataclass, field
import copy
from typing import Optional

from .timeprofile import DayOfWeek, TimeProfile

@dataclass
class TimeSlot:
    """Represents a specific time slot with start and end times"""
    start: datetime
    end: datetime
    
    @property
    def duration(self) -> timedelta:
        return self.end - self.start
        
    def overlaps(self, other: 'TimeSlot') -> bool:
        """Check if this slot overlaps with another"""
        return (self.start < other.end and self.end > other.start)
    
    def contains(self, dt: datetime) -> bool:
        """Check if this slot contains the given datetime"""
        return self.start <= dt < self.end
    
    def __hash__(self) -> int:
        return hash((self.start, self.end))
    
    def __str__(self) -> str:
        if self.start.date() == self.end.date():
            return f"{self.start.strftime('%Y-%m-%d %H:%M')} - {self.end.strftime('%H:%M')} ({self.duration})"
        else:
            return f"{self.start.strftime('%Y-%m-%d %H:%M')} - {self.end.strftime('%Y-%m-%d %H:%M')} ({self.duration})"


@dataclass
class TimeDomain:
    """A collection of available time slots within a scheduling period"""
    time_slots: list[TimeSlot] = field(default_factory=list)
    
    def add_slot(self, start: datetime, end: datetime) -> None:
        """Add a time slot to the map"""
        self.time_slots.append(TimeSlot(start, end))
    
    def remove_slot(self, slot: TimeSlot) -> None:
        """Remove a specific slot from the map"""
        self.time_slots.remove(slot)
    
    def find_conflicts(self, other: 'TimeDomain') -> list[tuple[TimeSlot, TimeSlot]]:
        """Find conflicts between this map and another"""
        conflicts = []
        for slot1 in self.time_slots:
            for slot2 in other.time_slots:
                if slot1.overlaps(slot2):
                    conflicts.append((slot1, slot2))
        return conflicts
    
    def is_time_available(self, start: datetime, end: datetime) -> bool:
        """Check if a specific time range is available"""
        return not any(slot.overlaps(TimeSlot(start, end)) for slot in self.time_slots)
    
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

    def apply_constraint(self, constraint: 'TimeDomain') -> 'TimeDomain':
        """Apply constraint by finding intersection with another TimeDomain"""
        result = TimeDomain()
        
        for slot1 in self.time_slots:
            for slot2 in constraint.time_slots:
                # Find intersection of slots
                if slot1.overlaps(slot2):
                    intersection_start = max(slot1.start, slot2.start)
                    intersection_end = min(slot1.end, slot2.end)
                    result.add_slot(intersection_start, intersection_end)
        
        return result

    def subtract(self, other: 'TimeDomain') -> None:
        """Subtract another TimeDomain from this one (this - other)"""        
        # For each slot in the other TimeDomain, remove its overlap from result
        for other_slot in other.time_slots:
            self.subtract_slot(other_slot)
            
    def subtract_slot(self, subtract_slot: TimeSlot) -> None:
        """
        Subtract a time slot from this TimeDomain
        Removes the overlapping portions of any slots in this domain
        """
        for slot in list(self.time_slots):  # Create a copy to avoid modification during iteration
            if slot.overlaps(subtract_slot):
                self._handle_slot_subtract(slot, subtract_slot)
                
    def _handle_slot_subtract(self, slot: TimeSlot, subtract_slot: TimeSlot) -> None:
        """
        Handle subtraction of one slot from another
        Removes the original slot and adds back non-overlapping portions
        """
        # Remove the original slot
        self.remove_slot(slot)
        
        # Case 1: Subtraction completely contains the slot - nothing to add back
        if subtract_slot.start <= slot.start and subtract_slot.end >= slot.end:
            return
        
        # Case 2: Subtraction splits the slot into two parts
        elif subtract_slot.start > slot.start and subtract_slot.end < slot.end:
            self.add_slot(slot.start, subtract_slot.start)
            self.add_slot(subtract_slot.end, slot.end)
        
        # Case 3: Subtraction covers the beginning of the slot
        elif subtract_slot.start <= slot.start and subtract_slot.end > slot.start and subtract_slot.end < slot.end:
            self.add_slot(subtract_slot.end, slot.end)
            
        # Case 4: Subtraction covers the end of the slot
        elif subtract_slot.start > slot.start and subtract_slot.start < slot.end and subtract_slot.end >= slot.end:
            self.add_slot(slot.start, subtract_slot.start)
                
                
    def trim_left(self, time_point : datetime) -> None:
        """Trim all slots to the left of the given time point"""
        for slot in sorted(self.time_slots, key=lambda x: x.start):
            if slot.end < time_point:
                self.remove_slot(slot)
            elif slot.start < time_point:
                self.add_slot(time_point, slot.end)
                self.remove_slot(slot)
                break
            else:
                break

    def trim_right(self, time_point : datetime) -> None:
        """Trim all slots to the right of the given time point"""
        for slot in sorted(self.time_slots, key=lambda x: x.start, reverse=True):
            if slot.start >= time_point:
                self.remove_slot(slot)
            elif slot.end > time_point:
                self.add_slot(slot.start, time_point)
                self.remove_slot(slot)
                break
            else:
                break


    def total_available_time(self) -> timedelta:
        """Calculate the total available time in this map"""
        return sum((slot.duration for slot in self.time_slots), timedelta())
    
    def copy(self) -> 'TimeDomain':
        """Create a deep copy of the TimeDomain"""
        return copy.deepcopy(self)

    def is_empty(self) -> bool:
        """Check if domain has any viable slots"""
        return len(self.time_slots) == 0

    def get_earliest_slot(self) -> Optional[TimeSlot]:
        """Get the earliest available slot"""
        return min(self.time_slots, key=lambda s: s.start) if self.time_slots else None

    
    def __str__(self) -> str:
        """Return a string representation of the TimeDomain"""
        if not self.time_slots:
            return "Empty TimeDomain"
        
        slots_str = "\n".join([f"  {slot.start.strftime('%Y-%m-%d %H:%M')} - {slot.end.strftime('%Y-%m-%d %H:%M')}" for slot in self.time_slots])
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
                start_date = min(slot.start for slot in self.time_slots)
            else:
                # Default to today
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Ensure start_date has time set to midnight
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Determine the end date
        end_date = start_date + timedelta(days=days)
        
        # Filter slots that fall within our visualization range
        visible_slots = [
            slot for slot in self.time_slots 
            if slot.end > start_date and slot.start < end_date
        ]
        
        if not visible_slots:
            return f"No time slots to visualize between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}"
        
        # Determine the hour range to display (default 8am-8pm if no slots in range)
        min_hour = min((slot.start.hour for slot in visible_slots), default=8)
        max_hour = max((slot.end.hour for slot in visible_slots), default=20)
        
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
                
                # Check if any slot overlaps with this hour
                has_slot = any(
                    slot.overlaps(TimeSlot(hour_start, hour_end))
                    for slot in visible_slots
                )
                
                if has_slot:
                    hour_str += " ███████████ |"
                else:
                    hour_str += "             |"
            
            result.append(hour_str)
        
        # Add final separator
        result.append(separator)
        
        print("\n".join(result))