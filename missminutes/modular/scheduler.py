from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import CpSolverSolutionCallback
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import math


class Task:
    def __init__(self, id: str, name: str, duration: float, est: datetime, lft: datetime,
                 min_session: float = 30, max_session: float = 240,
                 max_sessions_per_day: int = None, preferred_windows: List[Tuple[datetime, datetime]] = None):
        self.id = id
        self.name = name
        self.duration = duration
        self.est = est
        self.lft = lft
        self.min_session = min_session
        self.max_session = max_session
        self.max_sessions_per_day = max_sessions_per_day
        self.preferred_windows = preferred_windows or []

class Constraint(ABC):
    @abstractmethod
    def apply(self, model: cp_model.CpModel, task_vars: Dict[str, Dict], tasks: Dict[str, Task]):
        pass

class Objective(ABC):
    @abstractmethod
    def apply(self, model: cp_model.CpModel, task_vars: Dict[str, Dict], tasks: Dict[str, Task]) -> cp_model.IntVar:
        pass
    
class ModularScheduler:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.constraints: List[Constraint] = []
        self.objectives: List[Objective] = []
        self.model = cp_model.CpModel()
        self.debug = True
        self.solver_params = {
            'num_search_workers': 8,  # Parallel solving
            'log_search_progress': True
        }
        
    def datetime_to_minutes(self, dt: datetime) -> int:
        return int((dt - datetime(1970,1,1)).total_seconds() // 60)
    
    def minutes_to_datetime(self, minutes: int) -> datetime:
        return datetime(1970,1,1) + timedelta(minutes=minutes)
    
    def add_task(self, task: Task):
        self.tasks[task.id] = task
        
    def add_constraint(self, constraint: Constraint):
        self.constraints.append(constraint)
        
    def add_objective(self, objective: Objective):
        self.objectives.append(objective)
        
    def _create_task_vars(self) -> Dict[str, Dict]:
        task_vars = {}
        for task_id, task in self.tasks.items():
            est_min = self.datetime_to_minutes(task.est)
            lft_min = self.datetime_to_minutes(task.lft)
            min_dur = int(task.min_session)
            max_dur = int(task.max_session)
            
            # Calculate bounded number of sessions
            max_sessions = min(
                math.ceil(task.duration / task.min_session),
                10  # Reasonable upper bound
            )
            
            sessions = []
            for i in range(max_sessions):
                start = self.model.NewIntVar(est_min, lft_min, f"{task_id}_start_{i}")
                end = self.model.NewIntVar(est_min, lft_min, f"{task_id}_end_{i}")
                active = self.model.NewBoolVar(f"{task_id}_active_{i}")
                dur = self.model.NewIntVar(0, max_dur, f"{task_id}_dur_{i}")

                # Link duration to start/end only if active
                self.model.Add(end == start + dur).OnlyEnforceIf(active)
                self.model.Add(end == start).OnlyEnforceIf(active.Not())
                self.model.Add(dur >= min_dur).OnlyEnforceIf(active)
                
                sessions.append({
                    'start': start,
                    'end': end,
                    'duration': dur,
                    'active': active,
                    'interval': self.model.NewOptionalIntervalVar(
                        start, dur, end, active, f"{task_id}_interval_{i}"
                    )
                })
            
            # Total duration must match exactly
            active_durations = []
            for s in sessions:
                active_dur = self.model.NewIntVar(0, max_dur, f"{task_id}_active_dur_{i}")
                self.model.AddMultiplicationEquality(active_dur, s['duration'], s['active'])
                active_durations.append(active_dur)
            self.model.Add(sum(active_durations) == int(task.duration))
            
            task_vars[task_id] = {
                'sessions': sessions,
                'total_duration': sum(s['duration'] for s in sessions)
            }
            
            if self.debug:
                print(f"Created {max_sessions} sessions for {task_id}")
                
        return task_vars
        
    def solve(self) -> Dict:
        task_vars = self._create_task_vars()
        
        # Apply constraints
        for constraint in self.constraints:
            constraint.apply(self.model, task_vars, self.tasks)
            
        # Set objective
        if self.objectives:
            obj_vars = [obj.apply(self.model, task_vars, self.tasks) for obj in self.objectives]
            if len(obj_vars) == 1:
                self.model.Minimize(obj_vars[0])
            else:
                # Weighted sum approach
                weights = [1] * len(obj_vars)  # Adjust as needed
                weighted_sum = sum(w * v for w, v in zip(weights, obj_vars))
                self.model.Minimize(weighted_sum)
        
        # Configure and run solver
        solver = cp_model.CpSolver()
        for param, value in self.solver_params.items():
            setattr(solver.parameters, param, value)
        
        if self.debug:
            debug_cb = DebugSolutionCallback(task_vars, self.tasks)
            status = solver.SolveWithSolutionCallback(self.model, debug_cb)
        else:
            status = solver.Solve(self.model)
            
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return self._extract_solution(solver, task_vars)
        else:
            self._log_unsolved(status, solver)
            raise ValueError("No solution found")
    
    def _extract_solution(self, solver, task_vars):
        solution = {}
        for task_id, task in self.tasks.items():
            sessions = []
            for s in task_vars[task_id]['sessions']:
                if solver.Value(s['active']):
                    start = self.minutes_to_datetime(solver.Value(s['start']))
                    end = self.minutes_to_datetime(solver.Value(s['end']))
                    sessions.append((start, end))
            solution[task_id] = sessions
        return solution
    
    def _log_unsolved(self, status, solver):
        if status == cp_model.INFEASIBLE:
            print("Model is infeasible")
        elif status == cp_model.MODEL_INVALID:
            print("Model is invalid")
        else:
            print(f"Solver stopped with status {status}")
        print(f"Conflicts: {solver.NumConflicts()}")
        print(f"Branches: {solver.NumBranches()}")
        print(f"Wall time: {solver.WallTime()}s")

class DebugSolutionCallback(CpSolverSolutionCallback):
    def __init__(self, task_vars, tasks):
        super().__init__()
        self.task_vars = task_vars
        self.tasks = tasks
        
    def on_solution_callback(self):
        print("\n=== Current Solution ===")
        for task_id, task in self.tasks.items():
            active_count = sum(
                1 for s in self.task_vars[task_id]['sessions'] 
                if self.Value(s['active'])
            )
            print(f"\nTask {task_id} ({task.name}): {active_count} active sessions")
            
            for i, s in enumerate(self.task_vars[task_id]['sessions']):
                # if self.Value(s['active']):
                start = self.Value(s['start'])
                end = self.Value(s['end'])
                dur = end - start
                start_time = datetime(1970,1,1) + timedelta(minutes=start)
                end_time = datetime(1970,1,1) + timedelta(minutes=end)
                print(f"  Session {i}: {start_time.strftime('%a %I:%M %p')} - {end_time.strftime('%I:%M %p')} ({dur} mins)")