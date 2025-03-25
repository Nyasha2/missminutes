from scheduler import Objective
from ortools.sat.python import cp_model
from datetime import datetime

class MaximizePreference(Objective):
    def apply(self, model, task_vars, tasks):
        total_pref = model.NewIntVar(0, len(tasks)*100, "total_pref")
        pref_scores = []
        for task in tasks:
            if not task.preferred_windows:
                continue
            for session in task_vars[task.id]['sessions']:
                for window in task.preferred_windows:
                    window_start = int((window[0] - datetime(1970,1,1)).total_seconds() // 60)
                    window_end = int((window[1] - datetime(1970,1,1)).total_seconds() // 60)
                    in_window = model.NewBoolVar(f"{task.id}_pref_window")
                    model.Add(session['start'] >= window_start).OnlyEnforceIf(in_window)
                    model.Add(session['end'] <= window_end).OnlyEnforceIf(in_window)
                    pref_scores.append(in_window)
        model.Add(total_pref == sum(pref_scores))
        return -total_pref  # Negative because we maximize via minimization
    