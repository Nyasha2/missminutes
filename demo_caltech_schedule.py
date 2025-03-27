#!/usr/bin/env python3
"""
Caltech Week Schedule Demo

This demo showcases the scheduling capabilities of MissMinutes for a complex
college schedule with classes, assignments, meals, and other activities.
"""

from missminutes.scheduler import Scheduler
from missminutes.tasks import Task, RecurringTask, RecurrencePattern
from missminutes.timeprofile import TimeProfile, DayOfWeek
from missminutes.events import RecurringEvent
from datetime import datetime, timedelta

def main():
    # Set up start date for a typical week (starting on Monday)
    start_date = datetime(2023, 10, 2, 0, 0, 0)  # Monday
    days = 7  # Schedule for a week

    # Create a scheduler
    scheduler = Scheduler(start_date=start_date, days=days)

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
    for day in DayOfWeek:
        lunch_profile.add_window(day, 11, 0, 14, 0)
    scheduler.add_time_profile(lunch_profile)

    # Dinner time profile (5:30pm-7:30pm all days)
    dinner_profile = TimeProfile(name="Dinner Times")
    for day in DayOfWeek:
        dinner_profile.add_window(day, 17, 30, 19, 30)
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
    pe_class = RecurringEvent(
        id="pe_class",
        title="PE Class",
        start_time=start_date.replace(hour=9, minute=0),
        end_time=start_date.replace(hour=10, minute=20),
        completed=False
    )
    pe_class.set_weekly_recurrence(
        weekdays=[0, 2],  # Monday (0) and Wednesday (2)
        until=start_date + timedelta(days=days),
        interval=1
    )
    scheduler.add_event(pe_class)
    
    # CS130: Mondays, Wednesdays, Fridays, 11:00am to 12pm
    cs130_class = RecurringEvent(
        id="cs130_class",
        title="CS130 Class",
        start_time=start_date.replace(hour=11, minute=0),
        end_time=start_date.replace(hour=12, minute=0),
        completed=False
    )
    cs130_class.set_weekly_recurrence(
        weekdays=[0, 2, 4],  # Monday (0), Wednesday (2), Friday (4)
        until=start_date + timedelta(days=days),
        interval=1
    )
    scheduler.add_event(cs130_class)
    # CS4: Mondays, Wednesdays, Fridays, 3pm to 4pm
    cs4_class = RecurringEvent(
        id="cs4_class",
        title="CS4 Class",
        start_time=start_date.replace(hour=15, minute=0),
        end_time=start_date.replace(hour=16, minute=0),
        completed=False
    )
    cs4_class.set_weekly_recurrence(
        weekdays=[0, 2, 4],  # Monday (0), Wednesday (2), Friday (4)
        until=start_date + timedelta(days=days),
        interval=1
    )
    scheduler.add_event(cs4_class)

    # EE150: Tuesdays, Thursdays 10:30am to 12pm
    ee150_class = RecurringEvent(
        id="ee150_class",
        title="EE150 Class",
        start_time=(start_date + timedelta(days=1)).replace(hour=10, minute=30),  # Tuesday
        end_time=(start_date + timedelta(days=1)).replace(hour=12, minute=0),
        completed=False
    )
    ee150_class.set_weekly_recurrence(
        weekdays=[1, 3],  # Tuesday (1) and Thursday (3)
        until=start_date + timedelta(days=days),
        interval=1
    )
    scheduler.add_event(ee150_class)

    # CS172: Tuesdays, Thursdays 1pm to 2:25pm
    cs172_class = RecurringEvent(
        id="cs172_class",
        title="CS172 Class",
        start_time=(start_date + timedelta(days=1)).replace(hour=13, minute=0),  # Tuesday
        end_time=(start_date + timedelta(days=1)).replace(hour=14, minute=25),
        completed=False
    )
    cs172_class.set_weekly_recurrence(
        weekdays=[1, 3],  # Tuesday (1) and Thursday (3)
        until=start_date + timedelta(days=days),
        interval=1
    )
    scheduler.add_event(cs172_class)

    # Ec124: Tuesdays, Thursdays 2:30pm to 4:00pm
    ec124_class = RecurringEvent(
        id="ec124_class",
        title="Ec124 Class",
        start_time=(start_date + timedelta(days=1)).replace(hour=14, minute=30),  # Tuesday
        end_time=(start_date + timedelta(days=1)).replace(hour=16, minute=0),
        completed=False
    )
    ec124_class.set_weekly_recurrence(
        weekdays=[1, 3],  # Tuesday (1) and Thursday (3)
        until=start_date + timedelta(days=days),
        interval=1
    )
    scheduler.add_event(ec124_class)

    # ==== DAILY ROUTINE TASKS ====

    # Lunch (35-45 minutes between 11am-2pm weekdays)
    lunch_task = RecurringTask(
        title="Lunch",
        duration=timedelta(minutes=40),
        min_session_length=timedelta(minutes=35),
        max_session_length=timedelta(minutes=45)
    )
    lunch_task.set_recurrence(RecurrencePattern.DAILY, start_date, count=7)
    lunch_task.assign_time_profile(lunch_profile)
    scheduler.add_task(lunch_task)

    # Dinner (35-45 minutes between 5:30pm-7:30pm)
    dinner_task = RecurringTask(
        title="Dinner",
        duration=timedelta(minutes=40),
        min_session_length=timedelta(minutes=35),
        max_session_length=timedelta(minutes=45)
    )
    dinner_task.set_recurrence(RecurrencePattern.DAILY, start_date, count=7)
    dinner_task.assign_time_profile(dinner_profile)
    scheduler.add_task(dinner_task)

    # Gym session (1 hour + 40 min shower + 15 min travel)
    gym_task = RecurringTask(
        title="Gym Session",
        duration=timedelta(hours=1, minutes=55),  # 1h gym + 40m shower + 15m travel
        min_session_length=timedelta(hours=1, minutes=55),
        max_session_length=timedelta(hours=1, minutes=55)
    )
    gym_task.set_recurrence(RecurrencePattern.DAILY, start_date, count=7)
    gym_task.assign_time_profile(gym_profile)
    scheduler.add_task(gym_task)

    # ==== ASSIGNMENTS ====

    # CS130 Project (Released Friday 5pm, due next Friday 5pm, 12 hours)
    cs130_project = Task(
        title="CS130 Project Assignment",
        description="Released Friday 5pm, due next Friday 5pm",
        duration=timedelta(hours=12),
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
        min_session_length=timedelta(hours=1),
        max_session_length=timedelta(hours=3),
        due=start_date + timedelta(days=10)  # Next Thursday midnight
    )
    cs4_assignment.assign_time_profile(general_profile)
    scheduler.add_task(cs4_assignment)

    # EE150 Assignment (Released Tuesday, due next Tuesday, 9 hours)
    ee150_assignment = Task(
        title="EE150 Assignment",
        description="Released Tuesday, due next Tuesday",
        duration=timedelta(hours=9),
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
        min_session_length=timedelta(minutes=45),
        max_session_length=timedelta(hours=1, minutes=30),
        due=start_date + timedelta(days=7)  # Next Monday midnight
    )
    cs172_assignment.assign_time_profile(general_profile)
    scheduler.add_task(cs172_assignment)

    # Run the scheduler
    schedule = scheduler.schedule()

    # Visualize the schedule
    schedule_by_day = scheduler.print_schedule()

    # Print out the schedule for each day
    for date, sessions in schedule_by_day.items():
        date_obj = datetime.fromisoformat(date)
        print(f"\n=== {date_obj.strftime('%A, %B %d, %Y')} ===")
        if not sessions:
            print("No sessions scheduled.")
        else:
            # Sort sessions by start time
            sorted_sessions = sorted(sessions, key=lambda s: s['start_time'])
            
            # Find free time between sessions
            free_time_blocks = []
            for i in range(len(sorted_sessions) - 1):
                current_end = datetime.fromisoformat(sorted_sessions[i]['end_time'])
                next_start = datetime.fromisoformat(sorted_sessions[i+1]['start_time'])
                if next_start > current_end:
                    free_time_blocks.append((current_end, next_start))
            
            # Print sessions and free time in chronological order
            session_index = 0
            free_time_index = 0
            
            while session_index < len(sorted_sessions) or free_time_index < len(free_time_blocks):
                # Determine what comes next chronologically
                if free_time_index >= len(free_time_blocks) or (
                    session_index < len(sorted_sessions) and 
                    datetime.fromisoformat(sorted_sessions[session_index]['start_time']) < free_time_blocks[free_time_index][0]
                ):
                    # Print session
                    session = sorted_sessions[session_index]
                    start = datetime.fromisoformat(session['start_time'])
                    end = datetime.fromisoformat(session['end_time'])
                    duration = end - start
                    duration_str = f"({duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m)"
                    
                    if session['type'] == 'session':
                        print(f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} {duration_str}: {session['task_title']}")
                    elif session['type'] == 'event':
                        print(f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} {duration_str}: {session['title']}")
                    session_index += 1
                else:
                    # Print free time
                    start, end = free_time_blocks[free_time_index]
                    duration = end - start
                    duration_str = f"({duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m)"
                    print(f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} {duration_str}: FREE TIME")
                    free_time_index += 1

if __name__ == "__main__":
    main() 