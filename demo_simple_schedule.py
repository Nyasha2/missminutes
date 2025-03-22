#!/usr/bin/env python3
"""
Example demonstrating the use of MissMinutes scheduler with time map projections
"""

from datetime import datetime, timedelta
from missminutes import (
    TimeProfile, DayOfWeek, Task, Scheduler
)

def create_weekday_profile():
    """Create a time profile for weekdays 9am-5pm"""
    profile = TimeProfile("Weekdays 9-5")
    
    # Add 9am-5pm windows to weekdays
    weekdays = [
        DayOfWeek.MONDAY, 
        DayOfWeek.TUESDAY, 
        DayOfWeek.WEDNESDAY, 
        DayOfWeek.THURSDAY, 
        DayOfWeek.FRIDAY
    ]
    
    for day in weekdays:
        profile.add_window(day, 9, 0, 17, 0)
    
    return profile

def create_weekend_profile():
    """Create a time profile for weekends 10am-4pm"""
    profile = TimeProfile("Weekends 10-4")
    
    # Add 10am-4pm windows to weekends
    weekends = [DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]
    
    for day in weekends:
        profile.add_window(day, 10, 0, 16, 0)
    
    return profile

def main():
    # Create scheduler
    scheduler = Scheduler()
    
    # Create time profiles
    weekday_profile = create_weekday_profile()
    weekend_profile = create_weekend_profile()
    
    # Add profiles to scheduler
    scheduler.add_time_profile(weekday_profile)
    scheduler.add_time_profile(weekend_profile)
    
    # Create some tasks
    task1 = Task(
        title="Write report",
        description="Complete quarterly report",
        duration=timedelta(hours=4),
        due=datetime.now() + timedelta(days=3)
    )
    task1.assign_time_profile(weekday_profile)
    
    task2 = Task(
        title="Exercise",
        description="30-minute workout",
        duration=timedelta(minutes=30),
        due=datetime.now() + timedelta(days=7)
    )
    task2.assign_time_profile(weekend_profile)
    
    task3 = Task(
        title="Team meeting",
        description="Weekly team sync",
        duration=timedelta(hours=1),
        due=datetime.now() + timedelta(days=1),
        fixed_schedule=True
    )
    task3.assign_time_profile(weekday_profile)
    
    # Add tasks to scheduler
    scheduler.add_task(task1)
    scheduler.add_task(task2)
    scheduler.add_task(task3)
    
    # Schedule tasks for the next 7 days
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    sessions = scheduler.schedule(start_date, days=7)
    
    # Print schedule
    print(f"Scheduled {len(sessions)} sessions:")
    for session in sessions:
        task = scheduler.tasks[session.task_id]
        print(f"- {task.title}: {session.start_time.strftime('%Y-%m-%d %H:%M')} to {session.end_time.strftime('%H:%M')}")
    
    # Visualize schedule (for potential UI integration)
    schedule_by_day = scheduler.print_schedule()
    
    # Print schedule by day
    print("\nSchedule by day:")
    for date, day_sessions in schedule_by_day.items():
        if day_sessions:
            print(f"\n{date}:")
            for session_info in day_sessions:
                print(f"  - {session_info['task_title']}: {session_info['start_time'][11:16]} to {session_info['end_time'][11:16]}")

if __name__ == "__main__":
    main() 