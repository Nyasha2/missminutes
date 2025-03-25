from scheduler import Objective
from ortools.sat.python import cp_model
from datetime import datetime

class MaximizePreference(Objective):
    def apply(self, model, task_vars, tasks):
        total_pref = model.NewIntVar(0, len(tasks)*100, "total_pref")
        pref_scores = []
        
        for task_id, task in tasks.items():
            if not task.preferred_windows:
                continue
                
            for session in task_vars[task_id]['sessions']:
                # Only consider active sessions
                session_active = session['active']
                
                # Check against all preferred windows
                window_matches = []
                for window_start, window_end in task.preferred_windows:
                    w_start = int((window_start - datetime(1970,1,1)).total_seconds() // 60)
                    w_end = int((window_end - datetime(1970,1,1)).total_seconds() // 60)
                    
                    # Create boolean for this window match
                    matches_window = model.NewBoolVar(f"{task_id}_in_window_{w_start}_{w_end}")
                    
                    # Session must be fully contained in window
                    start_ok = model.NewBoolVar(f"{task_id}_start_ok")
                    end_ok = model.NewBoolVar(f"{task_id}_end_ok")
                    
                    model.Add(session['start'] >= w_start).OnlyEnforceIf(start_ok)
                    model.Add(session['start'] < w_start).OnlyEnforceIf(start_ok.Not())
                    
                    model.Add(session['end'] <= w_end).OnlyEnforceIf(end_ok)
                    model.Add(session['end'] > w_end).OnlyEnforceIf(end_ok.Not())
                    
                    model.AddBoolAnd([start_ok, end_ok]).OnlyEnforceIf(matches_window)
                    model.AddBoolOr([start_ok.Not(), end_ok.Not()]).OnlyEnforceIf(matches_window.Not())
                    
                    window_matches.append(matches_window)
                
                # Session gets preference if it matches ANY window
                if window_matches:
                    has_preference = model.NewBoolVar(f"{task_id}_has_preference")
                    model.AddBoolOr(window_matches).OnlyEnforceIf(has_preference)
                    model.AddBoolAnd([m.Not() for m in window_matches]).OnlyEnforceIf(has_preference.Not())
                    
                    # Only count if session is active
                    active_pref = model.NewBoolVar(f"{task_id}_active_pref")
                    model.AddBoolAnd([session_active, has_preference]).OnlyEnforceIf(active_pref)
                    model.AddBoolOr([session_active.Not(), has_preference.Not()]).OnlyEnforceIf(active_pref.Not())
                    
                    pref_scores.append(active_pref)
        
        model.Add(total_pref == sum(pref_scores))
        return -total_pref  # Negative for maximization
    