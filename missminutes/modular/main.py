from datetime import datetime
from scheduler import ModularScheduler, Task
from constraints import NonOverlapConstraint, DependencyConstraint, MaxSessionsPerDayConstraint
from objectives import MaximizePreference

# Initialize scheduler
scheduler = ModularScheduler()

# Define tasks
tasks = {
    "study": Task("study", "Study", 360, datetime(2023,9,1,9), datetime(2023,9,3,17),
         min_session=60, max_session=120,
         preferred_windows=[(datetime(2023,9,1,9), datetime(2023,9,1,12))]),
    "essay": Task("essay", "Essay", 240, datetime(2023,9,1,10), datetime(2023,9,3,16),
         max_sessions_per_day=4),
    "gym": Task("gym", "Gym", 60, datetime(2023,9,1,9), datetime(2023,9,3,20),
         preferred_windows=[(datetime(2023,9,1,17), datetime(2023,9,1,19))])
}

for task in tasks:
    scheduler.add_task(tasks[task])

# Add constraints
scheduler.add_constraint(NonOverlapConstraint())
scheduler.add_constraint(MaxSessionsPerDayConstraint())
scheduler.add_constraint(DependencyConstraint("essay", "study"))

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
print("Schedule:")
for day, sessions in sorted(days_schedule.items()):
    date_obj = datetime.strptime(day, '%Y-%m-%d')
    print(f"\n{date_obj.strftime('%A, %B %d, %Y')}:")
    # Sort sessions by start time
    for start, end, task_id in sorted(sessions, key=lambda x: x[0]):
        task_name = tasks[task_id].name
        duration = (end - start).total_seconds() / 60
        print(f"  {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} | {task_name} ({duration:.0f} min)")