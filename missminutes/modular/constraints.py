from scheduler import Constraint

class NonOverlapConstraint(Constraint):
    def apply(self, model, task_vars, tasks):
        all_intervals = []
        for task in tasks:
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
