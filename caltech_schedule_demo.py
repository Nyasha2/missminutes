#!/usr/bin/env python3
"""
Caltech Week Schedule Demo

This demo showcases the scheduling capabilities of MissMinutes for a complex
college schedule with classes, assignments, meals, and other activities.
"""

from missminutes.scheduler import Scheduler
from missminutes.tasks import Task
from missminutes.timeprofile import TimeProfile, DayOfWeek
from missminutes.events import Event
from datetime import datetime, timedelta

def main():
    # Set up start date for a typical week (starting on Monday)
    start_date = datetime(2023, 10, 2, 0, 0, 0)  # Monday
    days = 7  # Schedule for a week

    # Create a scheduler
    scheduler = Scheduler()

    # ==== TIME PROFILES ====

    # General availability profile (default available times)
    general_profile = TimeProfile(name="General Availability")

    # Setup weekdays with general availability (excluding sleep, late night, afternoon break)
    weekdays = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY
    ]
    
    # Available morning (8am to 12am)
    for day in weekdays:
        general_profile.add_window(day, 8, 0, 12, 0)
    
    # Available afternoon early (12pm to 4pm)
    for day in weekdays:
        general_profile.add_window(day, 12, 0, 16, 0)
    
    # Available afternoon late (5:30pm to 12am)
    for day in weekdays:
        general_profile.add_window(day, 17, 30, 23, 59)
    
    # Weekend availability (8am to 12am except Friday night)
    for day in [DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]:
        general_profile.add_window(day, 8, 0, 23, 59)
    
    # Friday is available until dinner only
    general_profile.day_schedules[DayOfWeek.FRIDAY].time_windows = []
    general_profile.add_window(DayOfWeek.FRIDAY, 8, 0, 19, 30)
        
    # Add the general profile to scheduler
    scheduler.add_time_profile(general_profile)

    # Lunch time profile (11am-2pm weekdays)
    lunch_profile = TimeProfile(name="Lunch Times")
    for day in weekdays:
        lunch_profile.add_window(day, 11, 0, 14, 0)
    scheduler.add_time_profile(lunch_profile)

    # Dinner time profile (5:30pm-7:30pm all days)
    dinner_profile = TimeProfile(name="Dinner Times")
    for day in DayOfWeek:
        dinner_profile.add_window(day, 17, 30, 19, 0)  # End by 7pm to finish by 7:30pm
    scheduler.add_time_profile(dinner_profile)

    # Gym time profile (preferred times 9am-12pm and 7pm-10pm)
    gym_profile = TimeProfile(name="Gym Times")
    for day in DayOfWeek:
        # Morning slot
        gym_profile.add_window(day, 9, 0, 12, 0)
        # Evening slot
        gym_profile.add_window(day, 19, 0, 22, 0)
    scheduler.add_time_profile(gym_profile)

    # ==== FIXED SCHEDULE EVENTS (CLASSES) ====

    # PE Class: Mondays, Wednesdays, 9am to 10:20am
    pe_mon = Event(
        id="pe_mon",
        title="PE Class",
        start_time=start_date.replace(hour=9, minute=0),
        end_time=start_date.replace(hour=10, minute=20),
        completed=False
    )
    
    pe_wed = Event(
        id="pe_wed",
        title="PE Class",
        start_time=(start_date + timedelta(days=2)).replace(hour=9, minute=0),
        end_time=(start_date + timedelta(days=2)).replace(hour=10, minute=20),
        completed=False
    )
    
    scheduler.add_event(pe_mon)
    scheduler.add_event(pe_wed)

    # CS130: Mondays, Wednesdays, Fridays, 11:00am to 12pm
    cs130_mon = Event(
        id="cs130_mon",
        title="CS130 Class",
        start_time=start_date.replace(hour=11, minute=0),
        end_time=start_date.replace(hour=12, minute=0),
        completed=False
    )
    
    cs130_wed = Event(
        id="cs130_wed",
        title="CS130 Class",
        start_time=(start_date + timedelta(days=2)).replace(hour=11, minute=0),
        end_time=(start_date + timedelta(days=2)).replace(hour=12, minute=0),
        completed=False
    )
    
    cs130_fri = Event(
        id="cs130_fri",
        title="CS130 Class",
        start_time=(start_date + timedelta(days=4)).replace(hour=11, minute=0),
        end_time=(start_date + timedelta(days=4)).replace(hour=12, minute=0),
        completed=False
    )
    
    scheduler.add_event(cs130_mon)
    scheduler.add_event(cs130_wed)
    scheduler.add_event(cs130_fri)

    # CS4: Mondays, Wednesdays, Fridays, 3pm to 4pm
    cs4_mon = Event(
        id="cs4_mon",
        title="CS4 Class",
        start_time=start_date.replace(hour=15, minute=0),
        end_time=start_date.replace(hour=16, minute=0),
        completed=False
    )
    
    cs4_wed = Event(
        id="cs4_wed",
        title="CS4 Class",
        start_time=(start_date + timedelta(days=2)).replace(hour=15, minute=0),
        end_time=(start_date + timedelta(days=2)).replace(hour=16, minute=0),
        completed=False
    )
    
    cs4_fri = Event(
        id="cs4_fri",
        title="CS4 Class",
        start_time=(start_date + timedelta(days=4)).replace(hour=15, minute=0),
        end_time=(start_date + timedelta(days=4)).replace(hour=16, minute=0),
        completed=False
    )
    
    scheduler.add_event(cs4_mon)
    scheduler.add_event(cs4_wed)
    scheduler.add_event(cs4_fri)

    # EE150: Tuesdays, Thursdays 10:30am to 12pm
    ee150_tue = Event(
        id="ee150_tue",
        title="EE150 Class",
        start_time=(start_date + timedelta(days=1)).replace(hour=10, minute=30),
        end_time=(start_date + timedelta(days=1)).replace(hour=12, minute=0),
        completed=False
    )
    
    ee150_thu = Event(
        id="ee150_thu",
        title="EE150 Class",
        start_time=(start_date + timedelta(days=3)).replace(hour=10, minute=30),
        end_time=(start_date + timedelta(days=3)).replace(hour=12, minute=0),
        completed=False
    )
    
    scheduler.add_event(ee150_tue)
    scheduler.add_event(ee150_thu)

    # CS172: Tuesdays, Thursdays 1pm to 2:25pm
    cs172_tue = Event(
        id="cs172_tue",
        title="CS172 Class",
        start_time=(start_date + timedelta(days=1)).replace(hour=13, minute=0),
        end_time=(start_date + timedelta(days=1)).replace(hour=14, minute=25),
        completed=False
    )
    
    cs172_thu = Event(
        id="cs172_thu",
        title="CS172 Class",
        start_time=(start_date + timedelta(days=3)).replace(hour=13, minute=0),
        end_time=(start_date + timedelta(days=3)).replace(hour=14, minute=25),
        completed=False
    )
    
    scheduler.add_event(cs172_tue)
    scheduler.add_event(cs172_thu)

    # Ec124: Tuesdays, Thursdays 2:30pm to 4:00pm
    ec124_tue = Event(
        id="ec124_tue",
        title="Ec124 Class",
        start_time=(start_date + timedelta(days=1)).replace(hour=14, minute=30),
        end_time=(start_date + timedelta(days=1)).replace(hour=16, minute=0),
        completed=False
    )
    
    ec124_thu = Event(
        id="ec124_thu",
        title="Ec124 Class",
        start_time=(start_date + timedelta(days=3)).replace(hour=14, minute=30),
        end_time=(start_date + timedelta(days=3)).replace(hour=16, minute=0),
        completed=False
    )
    
    scheduler.add_event(ec124_tue)
    scheduler.add_event(ec124_thu)

    # ==== DAILY ROUTINE TASKS ====

    # Lunch (35-45 minutes between 11am-2pm weekdays)
    lunch_task = Task(
        title="Lunch",
        duration=timedelta(minutes=40),
        fixed_schedule=False,
        min_session_length=timedelta(minutes=35),
        max_session_length=timedelta(minutes=45)
    )
    lunch_task.assign_time_profile(lunch_profile)
    scheduler.add_task(lunch_task)

    # Dinner (35-45 minutes between 5:30pm-7:30pm)
    dinner_task = Task(
        title="Dinner",
        duration=timedelta(minutes=40),
        fixed_schedule=False,
        min_session_length=timedelta(minutes=35),
        max_session_length=timedelta(minutes=45)
    )
    dinner_task.assign_time_profile(dinner_profile)
    scheduler.add_task(dinner_task)

    # Gym session (1 hour + 40 min shower + 15 min travel)
    gym_task = Task(
        title="Gym Session",
        duration=timedelta(hours=1, minutes=55),  # 1h gym + 40m shower + 15m travel
        fixed_schedule=False,
        min_session_length=timedelta(hours=1, minutes=55),
        max_session_length=timedelta(hours=1, minutes=55)
    )
    gym_task.assign_time_profile(gym_profile)
    scheduler.add_task(gym_task)

    # ==== ASSIGNMENTS ====

    # CS130 Project (Released Friday 5pm, due next Friday 5pm, 12 hours)
    cs130_project = Task(
        title="CS130 Project Assignment",
        description="Released Friday 5pm, due next Friday 5pm",
        duration=timedelta(hours=12),
        fixed_schedule=False,
        min_session_length=timedelta(hours=2),
        max_session_length=timedelta(hours=4),
        due=start_date + timedelta(days=11, hours=17)  # Next Friday 5pm
    )
    cs130_project.assign_time_profile(general_profile)
    scheduler.add_task(cs130_project)

    # CS4 Assignment (Released Thursday, due next Thursday, 4 hours)
    cs4_assignment = Task(
        title="CS4 Assignment",
        description="Released Thursday, due next Thursday",
        duration=timedelta(hours=4),
        fixed_schedule=False,
        min_session_length=timedelta(hours=1),
        max_session_length=timedelta(hours=2),
        due=start_date + timedelta(days=10)  # Next Thursday midnight
    )
    cs4_assignment.assign_time_profile(general_profile)
    scheduler.add_task(cs4_assignment)

    # EE150 Assignment (Released Tuesday, due next Tuesday, 9 hours)
    ee150_assignment = Task(
        title="EE150 Assignment",
        description="Released Tuesday, due next Tuesday",
        duration=timedelta(hours=9),
        fixed_schedule=False,
        min_session_length=timedelta(hours=1, minutes=30),
        max_session_length=timedelta(hours=3),
        due=start_date + timedelta(days=8)  # Next Tuesday midnight
    )
    ee150_assignment.assign_time_profile(general_profile)
    scheduler.add_task(ee150_assignment)

    # EE150 Paper Readings (Due Sunday midnight, 2 hours)
    ee150_readings = Task(
        title="EE150 Paper Readings",
        description="Due Sunday midnight",
        duration=timedelta(hours=2),
        fixed_schedule=False,
        min_session_length=timedelta(minutes=30),
        max_session_length=timedelta(hours=1),
        due=start_date + timedelta(days=6)  # Sunday midnight
    )
    ee150_readings.assign_time_profile(general_profile)
    scheduler.add_task(ee150_readings)

    # Ec124 Assignment (Released Tuesday, due next Tuesday, 3 hours)
    ec124_assignment = Task(
        title="Ec124 Assignment",
        description="Released Tuesday, due next Tuesday",
        duration=timedelta(hours=3),
        fixed_schedule=False,
        min_session_length=timedelta(hours=1),
        max_session_length=timedelta(hours=1, minutes=30),
        due=start_date + timedelta(days=8)  # Next Tuesday midnight
    )
    ec124_assignment.assign_time_profile(general_profile)
    scheduler.add_task(ec124_assignment)

    # CS172 Assignment (Released Monday, due next Monday, 3 hours)
    cs172_assignment = Task(
        title="CS172 Assignment",
        description="Released Monday, due next Monday",
        duration=timedelta(hours=3),
        fixed_schedule=False,
        min_session_length=timedelta(minutes=45),
        max_session_length=timedelta(hours=1, minutes=30),
        due=start_date + timedelta(days=7)  # Next Monday midnight
    )
    cs172_assignment.assign_time_profile(general_profile)
    scheduler.add_task(cs172_assignment)

    # Run the scheduler
    schedule = scheduler.schedule(start_date, days)

    # Visualize the schedule
    schedule_by_day = scheduler.visualize_schedule(start_date, days)

    # Print out the schedule for each day
    for date, sessions in schedule_by_day.items():
        print(f"\n=== {date} ===")
        if not sessions:
            print("No sessions scheduled.")
        else:
            # Sort sessions by start time
            sorted_sessions = sorted(sessions, key=lambda s: s['start_time'])
            for session in sorted_sessions:
                start = datetime.fromisoformat(session['start_time'])
                end = datetime.fromisoformat(session['end_time'])
                if session['type'] == 'session':
                    print(f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}: {session['task_title']}")
                elif session['type'] == 'event':
                    print(f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}: {session['title']}")

if __name__ == "__main__":
    main() 