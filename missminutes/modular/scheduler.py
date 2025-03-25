from ortools.sat.python import cp_model
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import math


class Task:
    def __init__(self, id: str, duration: float, est: datetime, lft: datetime,
                 min_session: float = 0.5, max_session: float = 4.0,
                 max_sessions_per_day: int = 3, preferred_windows: List[Tuple[datetime, datetime]] = None):
        self.id = id
        self.duration = duration
        self.est = est
        self.lft = lft
        self.min_session = min_session
        self.max_session = max_session
        self.max_sessions_per_day = max_sessions_per_day
        self.preferred_windows = preferred_windows or []

class Constraint(ABC):
    @abstractmethod
    def apply(self, model: cp_model.CpModel, task_vars: Dict[str, Dict], tasks: List[Task]):
        pass

class Objective(ABC):
    @abstractmethod
    def apply(self, model: cp_model.CpModel, task_vars: Dict[str, Dict], tasks: List[Task]) -> cp_model.IntVar:
        pass

class ModularScheduler:
    def __init__(self):
        self.tasks: List[Task] = []
        self.constraints: List[Constraint] = []
        self.objectives: List[Objective] = []
        self.model = cp_model.CpModel()
        
    def add_task(self, task: Task):
        self.tasks.append(task)
        
    def add_constraint(self, constraint: Constraint):
        self.constraints.append(constraint)
        
    def add_objective(self, objective: Objective):
        self.objectives.append(objective)
        
    def _create_task_vars(self) -> Dict[str, Dict]:
        task_vars = {}
        for task in self.tasks:
            est_min = int((task.est - datetime(1970,1,1)).total_seconds() // 60)
            lft_min = int((task.lft - datetime(1970,1,1)).total_seconds() // 60)
            min_dur = int(task.min_session * 60)
            max_dur = int(task.max_session * 60)
            
            # Calculate reasonable max sessions
            min_sessions = math.ceil(task.duration * 60 / max_dur)
            max_sessions = math.ceil(task.duration * 60 / min_dur)
        
            
            sessions = []
            for i in range(max_sessions):
                # Variable session duration
                start = self.model.NewIntVar(est_min, lft_min, f"{task.id}_start_{i}")
                end = self.model.NewIntVar(est_min, lft_min, f"{task.id}_end_{i}")

                # Session activation
                active = self.model.NewBoolVar(f"{task.id}_active_{i}")
                dur = self.model.NewIntVar(0, max_dur, f"{task.id}_dur_{i}")

                self.model.Add(dur >= min_dur).OnlyEnforceIf(active)
                self.model.Add(dur == 0).OnlyEnforceIf(active.Not())
                
                sessions.append({
                    'start': start,
                    'end': end,
                    'duration': dur,
                    'active': active,
                    'interval': self.model.NewOptionalIntervalVar(
                        start, dur, end, active, f"{task.id}_interval_{i}"
                    )
                })
            
            # Total duration constraint (exactly matches task duration)
            total_dur = sum(s['duration'] for s in sessions )
            self.model.Add(total_dur == int(task.duration * 60))
            
            # Minimum sessions constraint
            active_sessions = [s['active'] for s in sessions]
            self.model.Add(sum(active_sessions) >= min_sessions)
            
            task_vars[task.id] = {
                'sessions': sessions,
                'total_duration': total_dur
            }
        return task_vars
        
    def solve(self) -> Dict:
        task_vars = self._create_task_vars()
        
        # Apply constraints
        for constraint in self.constraints:
            constraint.apply(self.model, task_vars, self.tasks)
            
        # Set objective
        if self.objectives:
            obj_vars = [obj.apply(self.model, task_vars, self.tasks) for obj in self.objectives]
            self.model.Minimize(sum(obj_vars))
            
        # Solve with debug callback
        solver = cp_model.CpSolver()
        
        # Initialize and use the debug callback
        debug_cb = DebugSolutionCallback(task_vars, self.tasks)
        solver.parameters.log_search_progress = True  # Enable search progress logging too
        status = solver.SolveWithSolutionCallback(self.model, debug_cb)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            result = {}
            for task in self.tasks:
                sessions = []
                for s in task_vars[task.id]['sessions']:
                    start = datetime(1970,1,1) + timedelta(minutes=solver.Value(s['start']))
                    end = datetime(1970,1,1) + timedelta(minutes=solver.Value(s['end']))
                    if solver.Value(s['start']) < solver.Value(s['end']):  # Filter unused sessions
                        sessions.append((start, end))
                result[task.id] = sessions
            return result
        else:
            raise ValueError("No solution found")

class DebugSolutionCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, task_vars, tasks):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.task_vars = task_vars
        self.tasks = tasks
        
    def on_solution_callback(self):
        for task in self.tasks:
            print(f"Task {task.id}:")
            for i, s in enumerate(self.task_vars[task.id]['sessions']):
                active = self.Value(s['active'])
                dur = self.Value(s['duration'])
                print(f"  Session {i}: active={active}, dur={dur}")