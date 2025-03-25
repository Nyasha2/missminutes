from scheduler import Constraint
from datetime import datetime
class NonOverlapConstraint(Constraint):
    def apply(self, model, task_vars, tasks):
        all_intervals = []
        for _, task in tasks.items():
            all_intervals.extend([s['interval'] for s in task_vars[task.id]['sessions']])
        model.AddNoOverlap(all_intervals)

class DependencyConstraint(Constraint):
    def __init__(self, task_id: str, depends_on: str):
        self.task_id = task_id
        self.depends_on = depends_on
        
    def apply(self, model, task_vars, tasks):
        # Ensure all sessions of task_id start after all sessions of depends_on end
        # Get the bounds from the task variables
        est_min = min(s['end'].Proto().domain[0] for s in task_vars[self.depends_on]['sessions'])
        lft_min = max(s['end'].Proto().domain[1] for s in task_vars[self.depends_on]['sessions'])
        last_dep_end = model.NewIntVar(est_min, lft_min, "last_dep_end")
        model.AddMaxEquality(last_dep_end, [
            s['end'] for s in task_vars[self.depends_on]['sessions']
        ])
        
        for session in task_vars[self.task_id]['sessions']:
            model.Add(session['start'] >= last_dep_end)

class MaxSessionsPerDayConstraint(Constraint):
    def apply(self, model, task_vars, tasks):
        for task_id, task in tasks.items():
            if task.max_sessions_per_day is not None:
                start_day = int((task.est - datetime(1970,1,1)).total_seconds() // 86400)
                end_day = int((task.lft - datetime(1970,1,1)).total_seconds() // 86400)
               
                for day in range(start_day, end_day + 1):
                    day_session_flags = []
                    for i, session in enumerate(task_vars[task_id]['sessions']):
                        is_active_and_on_day = model.NewBoolVar(
                            f"{task_id}_session_{i}_active_on_day_{day}"
                        )
                        is_on_day = model.NewBoolVar(f"{task_id}_session_{i}_on_day_{day}")
                        session_day = model.NewIntVar(start_day, end_day, f"{task_id}_session_{i}_day")
                        model.AddDivisionEquality(session_day,session['start'], 1440)
                        model.Add(session_day == day).OnlyEnforceIf(is_on_day)
                        model.Add(session_day != day).OnlyEnforceIf(is_on_day.Not())
                        model.AddMultiplicationEquality(is_active_and_on_day, session['active'], is_on_day)
                        day_session_flags.append(is_active_and_on_day)
                    if len(day_session_flags) > 0:
                        model.Add(sum(day_session_flags) <= task.max_sessions_per_day)   
                