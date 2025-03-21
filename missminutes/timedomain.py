from datetime import datetime, timedelta
from dataclasses import dataclass, field
import copy

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
    
    def get_available_slots(self, min_duration: timedelta) -> list[TimeSlot]:
        """Get all slots with at least the specified duration"""
        return [slot for slot in self.time_slots if slot.duration >= min_duration]
    
    def find_conflicts(self, other: 'TimeDomain') -> list[tuple[TimeSlot, TimeSlot]]:
        """Find conflicts between this map and another"""
        conflicts = []
        for slot1 in self.time_slots:
            for slot2 in other.time_slots:
                if slot1.overlaps(slot2):
                    conflicts.append((slot1, slot2))
        return conflicts
    
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

    def subtract(self, other: 'TimeDomain') -> 'TimeDomain':
        """Subtract another TimeDomain from this one (this - other)"""
        result = copy.deepcopy(self)
        
        # For each slot in the other TimeDomain, remove its overlap from result
        for other_slot in other.time_slots:
            result.subtract_slot(other_slot)
        
        return result
    
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

    def total_available_time(self) -> timedelta:
        """Calculate the total available time in this map"""
        return sum((slot.duration for slot in self.time_slots), timedelta())