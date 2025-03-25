from datetime import datetime, timedelta
from scheduler import ModularScheduler, Task
from constraints import NonOverlapConstraint
from objectives import MaximizePreference

# Initialize scheduler
scheduler = ModularScheduler()

# Set up start date for a typical week (starting on Monday)
start_date = datetime(2023, 10, 2, 0, 0, 0)  # Monday
end_date = start_date + timedelta(days=7)    # Schedule for a week

# Define tasks
tasks = {}

# Daily routine tasks - breaking them down by day since no recurring task support
# Create lunch tasks for each day (weekdays only)
for day_offset in range(5):  # Monday to Friday
    day = start_date + timedelta(days=day_offset)
    task_id = "lunch_" + day.strftime("%a")
    tasks[task_id] = Task(
        task_id, 
        "Lunch",
        duration=40,  # 40 minutes
        est=day.replace(hour=11, minute=0),
        lft=day.replace(hour=14, minute=0),
        min_session=35,  # 35 minutes
        max_session=45,  # 45 minutes
    )

# Create dinner tasks for each day
for day_offset in range(7):  # Every day of the week
    day = start_date + timedelta(days=day_offset)
    task_id = "dinner_" + day.strftime("%a")
    tasks[task_id] = Task(
        task_id, 
        "Dinner",
        duration=40,  # 40 minutes
        est=day.replace(hour=17, minute=30),
        lft=day.replace(hour=19, minute=30),
        min_session=35,  # 35 minutes
        max_session=45,  # 45 minutes
    )

# Create gym sessions for each day
for day_offset in range(7):  # Every day of the week
    day = start_date + timedelta(days=day_offset)
    task_id = "gym_" + day.strftime("%a")
    tasks[task_id] = Task(
        task_id, 
        "Gym",
        duration=115,  # 1h55m (1h gym + 40m shower + 15m travel)
        est=day,
        lft=day.replace(hour=23, minute=59),
        min_session=115,
        max_session=115,
        preferred_windows=[
            (day.replace(hour=9, minute=0), day.replace(hour=12, minute=0)),
            (day.replace(hour=19, minute=0), day.replace(hour=22, minute=0)),
        ]
    )

# Create preferred windows for each day (simulating the general availability profile)
def get_general_preferred_windows(day):
    # Morning and early afternoon (8am-4pm)
    morning_window = (day.replace(hour=8, minute=0), day.replace(hour=16, minute=0))
    # Evening (5:30pm-midnight)
    evening_window = (day.replace(hour=17, minute=30), day.replace(hour=23, minute=59))
    return [morning_window, evening_window]

# Assignments with preferred windows
assignments = [
    Task("cs130_project", 
         name="CS130 Project",
         duration=720,  # 12 hours
         est=start_date,
         lft=start_date + timedelta(days=11, hours=17),  # Next Friday 5pm
         min_session=120,  # 2 hours
         max_session=240,  # 4 hours
         preferred_windows = sum([get_general_preferred_windows(start_date + timedelta(days=d)) 
                               for d in range(7)], [])
         ),
    
    Task("cs4_assignment", 
         name="CS4 Assignment",
         duration=240,  # 4 hours
         est=start_date,
         lft=start_date + timedelta(days=10),  # Next Thursday midnight
         min_session=60,  # 1 hour
         max_session=120,  # 2 hours
         preferred_windows = sum([get_general_preferred_windows(start_date + timedelta(days=d)) 
                               for d in range(7)], [])
         ),
    
    Task("ee150_assignment", 
         name="EE150 Assignment",
         duration=540,  # 9 hours
         est=start_date,
         lft=start_date + timedelta(days=8),  # Next Tuesday midnight
         min_session=90,  # 1.5 hours
         max_session=180,  # 3 hours
         preferred_windows = sum([get_general_preferred_windows(start_date + timedelta(days=d)) 
                               for d in range(7)], [])
         ),
    
    Task("ee150_readings", 
         name="EE150 Readings",
         duration=120,  # 2 hours
         est=start_date,
         lft=start_date + timedelta(days=6),  # Sunday midnight
         min_session=30,  # 30 minutes
         max_session=60,  # 1 hour
         # Add specific preference for weekend mornings
         preferred_windows = sum([get_general_preferred_windows(start_date + timedelta(days=d)) 
                               for d in range(7)], [])
         ),
    
    Task("ec124_assignment", 
         name="EC124 Assignment",
         duration=180,  # 3 hours
         est=start_date,
         lft=start_date + timedelta(days=8),  # Next Tuesday midnight
         min_session=60,  # 1 hour
         max_session=90,  # 1.5 hours
         preferred_windows = sum([get_general_preferred_windows(start_date + timedelta(days=d)) 
                               for d in range(7)], [])
         ),
    
        Task("cs172_assignment", 
         name="CS172 Assignment",
         duration=180,  # 3 hours
         est=start_date,
         lft=start_date + timedelta(days=7),  # Next Monday midnight
         min_session=45,  # 45 minutes
         max_session=90,  # 1.5 hours
         # Add specific preference for after CS172 class on Thursdays
         preferred_windows = sum([get_general_preferred_windows(start_date + timedelta(days=d)) 
                               for d in range(7)], [])
         )
]
tasks.update([(t.id, t) for t in assignments])

# Define fixed class events as unavailable time slots
fixed_events = [
    # PE Class: Mondays, Wednesdays, 9am to 10:20am
    ("pe_class", 
     "PE Class",
     [start_date.replace(hour=9, minute=0),  # Monday
      (start_date + timedelta(days=2)).replace(hour=9, minute=0)],  # Wednesday
     [start_date.replace(hour=10, minute=20),  # Monday
      (start_date + timedelta(days=2)).replace(hour=10, minute=20)]),  # Wednesday
    
    # CS130: Mondays, Wednesdays, Fridays, 11am to 12pm
    ("cs130_class",
     "CS130 Class",
     [start_date.replace(hour=11, minute=0),  # Monday
      (start_date + timedelta(days=2)).replace(hour=11, minute=0),  # Wednesday
      (start_date + timedelta(days=4)).replace(hour=11, minute=0)],  # Friday
     [start_date.replace(hour=12, minute=0),  # Monday
      (start_date + timedelta(days=2)).replace(hour=12, minute=0),  # Wednesday
      (start_date + timedelta(days=4)).replace(hour=12, minute=0)]),  # Friday
    
    # CS4: Mondays, Wednesdays, Fridays, 3pm to 4pm
    ("cs4_class",
     "CS4 Class",
     [start_date.replace(hour=15, minute=0),  # Monday
      (start_date + timedelta(days=2)).replace(hour=15, minute=0),  # Wednesday
      (start_date + timedelta(days=4)).replace(hour=15, minute=0)],  # Friday
     [start_date.replace(hour=16, minute=0),  # Monday
      (start_date + timedelta(days=2)).replace(hour=16, minute=0),  # Wednesday
      (start_date + timedelta(days=4)).replace(hour=16, minute=0)]),  # Friday
    
    # EE150: Tuesdays, Thursdays, 10:30am to 12pm
    ("ee150_class",
     "EE150 Class",
     [(start_date + timedelta(days=1)).replace(hour=10, minute=30),  # Tuesday
      (start_date + timedelta(days=3)).replace(hour=10, minute=30)],  # Thursday
     [(start_date + timedelta(days=1)).replace(hour=12, minute=0),  # Tuesday
      (start_date + timedelta(days=3)).replace(hour=12, minute=0)]),  # Thursday
    
    # CS172: Tuesdays, Thursdays, 1pm to 2:25pm
    ("cs172_class",
     "CS172 Class",
     [(start_date + timedelta(days=1)).replace(hour=13, minute=0),  # Tuesday
      (start_date + timedelta(days=3)).replace(hour=13, minute=0)],  # Thursday
     [(start_date + timedelta(days=1)).replace(hour=14, minute=25),  # Tuesday
      (start_date + timedelta(days=3)).replace(hour=14, minute=25)]),  # Thursday
    
    # Ec124: Tuesdays, Thursdays, 2:30pm to 4pm
    ("ec124_class",
     "EC124 Class",
     [(start_date + timedelta(days=1)).replace(hour=14, minute=30),  # Tuesday
      (start_date + timedelta(days=3)).replace(hour=14, minute=30)],  # Thursday
     [(start_date + timedelta(days=1)).replace(hour=16, minute=0),  # Tuesday
      (start_date + timedelta(days=3)).replace(hour=16, minute=0)]),  # Thursday
]

# Add fixed events as unavailable blocks by representing them as tasks with specific times
for event_id, event_name, starts, ends in fixed_events:
    for start, end in zip(starts, ends):
        duration_minutes = int((end - start).total_seconds() / 60)
        # Create a task that is fixed to this time slot
        task_id = f"blocked_{event_id}_{start.strftime('%a_%H%M')}"
        tasks[task_id] = Task(
            task_id,
            event_name,
            duration=duration_minutes,
            est=start,
            lft=end,
            min_session=duration_minutes,
            max_session=duration_minutes
        )

# Add all tasks to scheduler
for task in tasks:
    scheduler.add_task(tasks[task])

# Add constraints
scheduler.add_constraint(NonOverlapConstraint())

# Add objectives
scheduler.add_objective(MaximizePreference())

# Solve
result = scheduler.solve()

# Organize sessions by day
days_schedule = {}
for task_id, sessions in result.items():
    for start, end in sessions:
        day_key = start.strftime('%Y-%m-%d')
        if day_key not in days_schedule:
            days_schedule[day_key] = []
        days_schedule[day_key].append((start, end, task_id))

# Print schedule organized by days
print("Caltech Schedule:")
for day, sessions in sorted(days_schedule.items()):
    date_obj = datetime.strptime(day, '%Y-%m-%d')
    print(f"\n{date_obj.strftime('%A, %B %d, %Y')}:")
    # Sort sessions by start time
    for start, end, task_id in sorted(sessions, key=lambda x: x[0]):
        task_name = tasks[task_id].name
        duration_mins = (end - start).total_seconds() / 60
        print(f"  {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} | {task_name} ({duration:.0f} min)")