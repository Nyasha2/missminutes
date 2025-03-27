from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
import uuid
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU
from .timedomain import TimeDomain


@dataclass
class Event:
    """An event with a fixed schedule"""
    # Basic info
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None

    # Organization
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
        
    # Status
    completed: bool = False
    
    @property
    def duration(self) -> timedelta:
        """Get the duration of the event"""
        return self.end_time - self.start_time
    
    def conflicts_with(self, other: 'Event') -> bool:
        """Check if this event conflicts with another event"""
        return (self.start_time < other.end_time and 
                self.end_time > other.start_time)
    
    def to_time_domain(self) -> TimeDomain:
        """Convert event to a time domain with a single slot"""
        domain = TimeDomain()
        domain.add_slot(self.start_time, self.end_time)
        return domain
    
    def mark_complete(self) -> None:
        """Mark the event as completed"""
        self.completed = True
    

@dataclass
class RecurringEvent(Event):
    """An event that recurs according to a schedule"""
    # Recurrence specific fields
    recurrence_rule: Optional[rrule] = None  # dateutil rrule for recurrence
    recurrence_until: Optional[datetime] = None  # When recurrence ends
    recurrence_count: Optional[int] = None  # Number of occurrences
    recurrence_interval: int = 1  # Interval between occurrences
    
    # Weekdays for weekly recurrence (0=MO, 1=TU, etc.)
    recurrence_weekdays: list[int] = field(default_factory=list)
    
    # Days of month for monthly recurrence
    recurrence_monthdays: list[int] = field(default_factory=list)
    
    # Months for yearly recurrence
    recurrence_months: list[int] = field(default_factory=list)
    
    # For keeping track of generated occurrences
    occurrence_ids: list[str] = field(default_factory=list)
    
    def set_daily_recurrence(self, 
                         until: Optional[datetime] = None,
                         count: Optional[int] = None,
                         interval: int = 1) -> None:
        """Set up daily recurrence"""
        self.recurrence_interval = interval
        self.recurrence_until = until
        self.recurrence_count = count
        
        # Create the rrule
        kwargs = {'freq': DAILY, 'dtstart': self.start_time, 'interval': interval}
        if until:
            kwargs['until'] = until
        if count:
            kwargs['count'] = count
            
        self.recurrence_rule = rrule(**kwargs)
    
    def set_weekly_recurrence(self, 
                          weekdays: list[int],  # 0=MO, 1=TU, etc.
                          until: Optional[datetime] = None,
                          count: Optional[int] = None,
                          interval: int = 1) -> None:
        """Set up weekly recurrence"""
        self.recurrence_weekdays = weekdays
        self.recurrence_interval = interval
        self.recurrence_until = until
        self.recurrence_count = count
        
        # Convert weekday integers to dateutil constants
        byweekday = []
        weekday_map = {0: MO, 1: TU, 2: WE, 3: TH, 4: FR, 5: SA, 6: SU}
        for day in weekdays:
            byweekday.append(weekday_map[day])
            
        # Create the rrule
        kwargs = {
            'freq': WEEKLY, 
            'dtstart': self.start_time, 
            'interval': interval,
            'byweekday': byweekday
        }
        if until:
            kwargs['until'] = until
        if count:
            kwargs['count'] = count
            
        self.recurrence_rule = rrule(**kwargs)
    
    def set_monthly_recurrence(self, 
                           monthdays: Optional[list[int]] = None,  # Days of month
                           until: Optional[datetime] = None,
                           count: Optional[int] = None,
                           interval: int = 1) -> None:
        """Set up monthly recurrence"""
        self.recurrence_monthdays = monthdays or []
        self.recurrence_interval = interval
        self.recurrence_until = until
        self.recurrence_count = count
        
        # Create the rrule
        kwargs = {'freq': MONTHLY, 'dtstart': self.start_time, 'interval': interval}
        if monthdays:
            kwargs['bymonthday'] = monthdays
        if until:
            kwargs['until'] = until
        if count:
            kwargs['count'] = count
            
        self.recurrence_rule = rrule(**kwargs)
    
    def set_yearly_recurrence(self, 
                          months: Optional[list[int]] = None,  # Months (1-12)
                          monthdays: Optional[list[int]] = None,  # Days of month
                          until: Optional[datetime] = None,
                          count: Optional[int] = None,
                          interval: int = 1) -> None:
        """Set up yearly recurrence"""
        self.recurrence_months = months or []
        self.recurrence_monthdays = monthdays or []
        self.recurrence_interval = interval
        self.recurrence_until = until
        self.recurrence_count = count
        
        # Create the rrule
        kwargs = {'freq': YEARLY, 'dtstart': self.start_time, 'interval': interval}
        if months:
            kwargs['bymonth'] = months
        if monthdays:
            kwargs['bymonthday'] = monthdays
        if until:
            kwargs['until'] = until
        if count:
            kwargs['count'] = count
            
        self.recurrence_rule = rrule(**kwargs)
    
    def get_occurrences(self, start: datetime, end: datetime) -> list['Event']:
        """
        Get all occurrences of this event within a date range
        
        Returns regular Event objects (not RecurringEvent)
        """
        if not self.recurrence_rule:
            # If no recurrence rule, just return this event if it falls within range
            if self.start_time >= start and self.start_time <= end:
                return [self]
            return []
            
        # Calculate the duration of the event to apply to each occurrence
        duration = self.duration
        
        # Get all occurrence datetimes within the range
        occurrences = list(self.recurrence_rule.between(start, end, inc=True))
        
        # Create Event objects for each occurrence
        result = []
        for occurrence_dt in occurrences:
            # Skip if this occurrence is outside range
            if occurrence_dt < start or occurrence_dt > end:
                continue
                
            # Create a new Event with the same properties but different times
            occurrence = Event(
                title=self.title,
                description=self.description,
                start_time=occurrence_dt,
                end_time=occurrence_dt + duration,
                id=str(uuid.uuid4()),  # Generate a new ID for this occurrence
                parent_id=self.id,     # Set parent to this recurring event
                completed=self.completed,
            )
            
            # Add the occurrence ID to our tracking list
            self.occurrence_ids.append(occurrence.id)
            
            result.append(occurrence)
            
        return result
        
    @classmethod
    def from_event(cls, event: Event, **recurrence_kwargs) -> 'RecurringEvent':
        """
        Create a RecurringEvent from a regular Event
        
        Args:
            event: The existing Event to convert
            **recurrence_kwargs: Recurrence parameters to pass to set_recurrence methods
            
        Returns:
            A new RecurringEvent instance with all the original event's properties
        """
        recurring_event = cls(
            title=event.title,
            description=event.description,
            location=event.location,
            event_type=event.event_type,
            start_time=event.start_time,
            end_time=event.end_time,
            all_day=event.all_day,
            id=event.id,  # Keep the same ID
            parent_id=event.parent_id,
            tags=event.tags.copy(),
            color=event.color,
            completed=event.completed,
            cancelled=event.cancelled,
            attendees=event.attendees.copy()
        )
        
        # Set up recurrence if parameters were provided
        if recurrence_kwargs:
            pattern = recurrence_kwargs.pop('pattern', 'daily')
            if pattern == 'daily':
                recurring_event.set_daily_recurrence(**recurrence_kwargs)
            elif pattern == 'weekly':
                recurring_event.set_weekly_recurrence(**recurrence_kwargs)
            elif pattern == 'monthly':
                recurring_event.set_monthly_recurrence(**recurrence_kwargs)
            elif pattern == 'yearly':
                recurring_event.set_yearly_recurrence(**recurrence_kwargs)
                
        return recurring_event 