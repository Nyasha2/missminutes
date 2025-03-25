from datetime import datetime
from scheduler import ModularScheduler, Task
from constraints import NonOverlapConstraint, DependencyConstraint
from objectives import MaximizePreference

# Initialize scheduler
scheduler = ModularScheduler()

# Define tasks
tasks = [
    Task("study", 6, datetime(2023,9,1,9), datetime(2023,9,3,17),
         min_session=1.0, max_session=2.0,
         preferred_windows=[(datetime(2023,9,1,9), datetime(2023,9,1,12))]),
    Task("essay", 4.0, datetime(2023,9,1,10), datetime(2023,9,3,16),
         max_sessions_per_day=1),
    Task("gym", 1.0, datetime(2023,9,1,9), datetime(2023,9,3,20),
         preferred_windows=[(datetime(2023,9,1,17), datetime(2023,9,1,19))])
]

for task in tasks:
    scheduler.add_task(task)

# Add constraints
scheduler.add_constraint(NonOverlapConstraint())
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
        duration = (end - start).total_seconds() / 60
        print(f"  {start.strftime('%H:%M')} - {end.strftime('%H:%M')} | {task_id} ({duration:.0f} min)")