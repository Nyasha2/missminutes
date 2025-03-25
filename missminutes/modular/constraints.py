from scheduler import Constraint
from datetime import datetime
from ortools.sat.python import cp_model
class NonOverlapConstraint(Constraint):
    def apply(self, model, task_vars, tasks):
        all_intervals = []
        for task_id, task in tasks.items():
            sessions = task_vars[task.id]['sessions']
            
            # First enforce no-overlap within the same task
            task_intervals = [s['interval'] for s in sessions]
            model.AddNoOverlap(task_intervals)
            
            # Collect for global no-overlap
            all_intervals.extend(task_intervals)
        
        # Global no-overlap
        model.AddNoOverlap(all_intervals)
        

class DependencyConstraint(Constraint):
    def __init__(self, task_id: str, depends_on: str):
        self.task_id = task_id
        self.depends_on = depends_on
        
    def apply(self, model, task_vars, tasks):
        # Get the latest end time of all ACTIVE sessions in the dependency task
        active_ends = []
        for session in task_vars[self.depends_on]['sessions']:
            # Only consider active sessions
            active_end = model.NewIntVar(0, cp_model.INT32_MAX, f"{self.depends_on}_active_end")
            model.Add(active_end == session['end']).OnlyEnforceIf(session['active'])
            model.Add(active_end == 0).OnlyEnforceIf(session['active'].Not())
            active_ends.append(active_end)
        
        # Find the maximum end time among active sessions
        if active_ends:
            last_dep_end = model.NewIntVar(0, cp_model.INT32_MAX, "last_dep_end")
            model.AddMaxEquality(last_dep_end, active_ends)
            
            # All sessions of the dependent task must start after this
            for session in task_vars[self.task_id]['sessions']:
                # Only enforce if this session is active
                model.Add(session['start'] >= last_dep_end).OnlyEnforceIf(session['active'])
                
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
                        # session['day'] = session_day
                        # session['is_on_day'] = is_on_day
                    if len(day_session_flags) > 0:
                        model.Add(sum(day_session_flags) <= task.max_sessions_per_day)   
                