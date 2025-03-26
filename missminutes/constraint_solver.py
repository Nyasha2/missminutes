from dataclasses import dataclass
from datetime import datetime, timedelta
from .timedomain import TimeDomain, TimeSlot
from .tasks import Task, Session, Event, DependencyType
import uuid
from collections import defaultdict
import heapq

def calculate_overlap_metric(domain: TimeDomain, weighted_intervals: dict[TimeSlot, int]) -> float:
    """Calculate the overlap metric for a time domain"""
    assert not domain.is_empty(), f"calculate_overlap_metric: empty time domain"
    assert weighted_intervals, f"calculate_overlap_metric: empty weighted_intervals"
    total_weight = 0
    total_duration = 0

    i = 0
    wt_slots = list(weighted_intervals.keys())
    for slot in sorted(domain.time_slots, key=lambda x: x.start):
        # fast forward to wt_slot that starts at slot.start
        while i < len(wt_slots) and wt_slots[i].start < slot.start:
            i += 1
        while i < len(wt_slots) and wt_slots[i].end <= slot.end:
            weight = weighted_intervals[wt_slots[i]] * wt_slots[i].duration.total_seconds()
            total_weight += weight
            i += 1  
        slot_duration = slot.duration.total_seconds()
        total_duration += slot_duration
    return total_weight / total_duration

def sorted_slots(domain: TimeDomain, weighted_intervals: dict[TimeSlot, int]) -> list[TimeSlot]:
    """Sort slots in domain by weighted_intervals. Least constrained slots come first."""
    assert not domain.is_empty(), f"sorted_slots: empty time domain"
    weighted_slots = defaultdict(int)
    i = 0
    wt_slots = list(weighted_intervals.keys())
    for slot in sorted(domain.time_slots, key=lambda x: x.start):
        while i < len(wt_slots) and wt_slots[i].start < slot.start:
            i += 1
        while i < len(wt_slots) and wt_slots[i].end <= slot.end:
            weighted_slots[slot] += weighted_intervals[wt_slots[i]] * wt_slots[i].duration.total_seconds()
            i += 1
        weighted_slots[slot] /= slot.duration.total_seconds()
    return sorted(domain.time_slots, key=lambda x: weighted_slots[x])

def remove_overlap_weighting(domain: TimeDomain, weighted_intervals: dict[TimeSlot, int]) -> None:
    """Remove overlapping weighting from weighted_intervals"""
    i = 0
    wt_slots = list(weighted_intervals.keys())
    for slot in sorted(domain.time_slots, key=lambda x: x.start):
        while i < len(wt_slots) and wt_slots[i].start < slot.start:
            i += 1
        while i < len(wt_slots) and wt_slots[i].end <= slot.end:
            weighted_intervals[wt_slots[i]] -= 1
            i += 1

def apply_min_session_length_constraint(domain: TimeDomain, min_session_length: timedelta) -> None:
    """Remove all slots with duration less than min_session_length"""
    for slot in domain.time_slots:
        if slot.duration < min_session_length:
            domain.remove_slot(slot)


@dataclass
class SchedulingDecision:
    """Represents a scheduling decision for backtracking"""
    task_id: str
    assigned_sessions: list[Session]
    domain_changes: dict[str, TimeDomain] # taskid -> change domain


@dataclass
class ConstraintSolver:
    def weighted_time_slots(self, domains: list[TimeDomain]) -> dict[TimeSlot, int]:
        """
        Breaks existing domain intervals into more granular intervals which
        are then weighted by the number of intersecting domains.
        Returns sorted dict of sub-intervals to weights.
        """
        interval_boundaries = set()
        for domain in domains:
            for slot in domain.time_slots:
                interval_boundaries.add(slot.start)
                interval_boundaries.add(slot.end)
        
        sorted_boundaries = sorted(interval_boundaries)

        sub_intervals : list[TimeSlot] = []
        for i in range(len(sorted_boundaries) - 1):
            start = sorted_boundaries[i]
            end = sorted_boundaries[i + 1]
            if start < end:
                sub_intervals.append(TimeSlot(start, end))

        weighted_intervals : dict[TimeSlot, int] = defaultdict(int)
        for sub_interval in sub_intervals:
            for domain in domains:
                for slot in domain.time_slots:
                    if (slot.start <= sub_interval.start and 
                        slot.end >= sub_interval.end):
                        weighted_intervals[sub_interval] += 1

        return weighted_intervals



    def topo_rank(self, tasks: list[Task]) -> dict[str, int]:
        """Topological sort of tasks. Returns a dict of task id to rank"""
        # TODO: needs testing
        # Create dependency graph
        graph = defaultdict(set)
        for task in tasks:
            graph[task.id] = set()
            for dep_id, dep_type in task.task_dependencies.items():
                if dep_type == DependencyType.AFTER:
                    graph[task.id].add(dep_id)
        
        # Find ranks using topological sort
        ranks = {}
        visited = set()
        temp_visited = set()
        
        def visit(node_id, current_rank=0):
            if node_id in temp_visited:
                # Cycle detected
                raise ValueError(f"Cycle detected in task dependencies: {node_id}")
            if node_id in visited:
                return
            
            temp_visited.add(node_id)
            
            # Visit all dependencies first
            max_dep_rank = current_rank
            if node_id in graph:
                for dep_id in graph[node_id]:
                    visit(dep_id, current_rank + 1)
                    if dep_id in ranks:
                        max_dep_rank = max(max_dep_rank, ranks[dep_id] + 1)
            
            # Assign rank based on dependencies
            ranks[node_id] = max_dep_rank
            visited.add(node_id)
            temp_visited.remove(node_id)
        
        # Visit all nodes
        for task in tasks:
            if task.id not in visited:
                visit(task.id)
        
        return ranks


    def presolve(self, tasks: list[Task], events: list[Event], start_date: datetime, days: int) -> tuple[dict[TimeSlot, int], list[tuple[int, float, Task, TimeDomain]]]:
        """Presolving step to prune task domains and sort them by dependency and overlap"""
        num_tasks = len(tasks)
        num_events = len(events)
        print(f"Starting presolve with {num_tasks} tasks and {num_events} events")
        tasks_domains : list[tuple[Task, TimeDomain]] = []
        events_domain = TimeDomain()
        events_map : dict[str, Event] = {}
        for event in events:
            events_domain.add_slot(event.start_time, event.end_time)
            events_map[event.id] = event

        # apply constraints to task domains
        for task in tasks:
            task_domain = task.time_domain(start_date, days).copy()
            task_domain.subtract(events_domain)
            assert not task_domain.is_empty(), f'presolve: Task "{task.title}" domain is empty after applying event constraints'
            
            for dep_id, dep_type in task.event_dependencies.items():
                if dep_type == DependencyType.AFTER:
                    task_domain.trim_left(events_map[dep_id].end_time)
                elif dep_type == DependencyType.BEFORE:
                    task_domain.trim_right(events_map[dep_id].start_time)
                elif dep_type == DependencyType.DURING:
                    task_domain = TimeDomain([TimeSlot(events_map[dep_id].start_time, events_map[dep_id].end_time)])
            tasks_domains.append((task, task_domain))

        
        topo_ranks = self.topo_rank(tasks)
        weighted_intervals = self.weighted_time_slots([domain for _, domain in tasks_domains])
        sorted_tasks_with_domains : list[tuple[int, float, Task, TimeDomain]] = []  
        for task, domain in tasks_domains:
            assert not domain.is_empty(), f'presolve: Task "{task.title}" domain is empty after applying constraints'
            overlap_metric = calculate_overlap_metric(domain, weighted_intervals)
            heapq.heappush(sorted_tasks_with_domains, (topo_ranks[task.id], -overlap_metric, task, domain))
        
        return weighted_intervals, sorted_tasks_with_domains
    
        
    def solve(self, tasks: list[Task], events: list[Event], start_date: datetime, days: int) -> list[Session]:
        """Solve scheduling problem using backtracking"""
        weighted_intervals, tasks_with_domains = self.presolve(tasks, events, start_date, days)
        
        scheduled_sessions: list[Session] = []

        print(f"Starting solve with heap size {len(tasks_with_domains)}")
        while tasks_with_domains:
            print(f"Heap size: {len(tasks_with_domains)}")
            topo_rank, _, task, current_domain = heapq.heappop(tasks_with_domains)
            
            print(f"Attempting to schedule task {task.title} with remaining duration {task.get_remaining_duration()}")
            
            # assert task.get_remaining_duration() >= task.min_session_length, f'Task "{task.title}" has min session length {task.min_session_length} > remaining duration {task.get_remaining_duration()}'
            
            # constraints already applied:
            #1. deadline constraint (domain doesn't go beyond deadline)
            #2. preferred window constraint (domain doesn't go beyond preferred window or is weighted by preferred window)
            #3. task dependency constraint (tasks are topo sorted)
            
            apply_min_session_length_constraint(current_domain, task.min_session_length)
            assert current_domain.total_available_time() >= task.get_remaining_duration(), f'Task "{task.title}" domain ran out of time after min session length constraint'
            #5. break time constraint
            slots = sorted_slots(current_domain, weighted_intervals)
            assert slots, f'Task "{task.title}" domain has no slots after min session length constraint'
            
            print(f"Available slots: \n{'\n'.join(['\t' + str(slot) for slot in slots])}")
            # Try first available slot
            best_slot = slots[0]
            
            session_duration = min(
                task.get_remaining_duration(),
                task.max_session_length or best_slot.duration,
                best_slot.duration
            ) # this intrinsically applies the max session length constraint
            
            session = Session(
                task_id=task.id,
                session_id=str(uuid.uuid4()),
                start_time=best_slot.start,
                end_time=best_slot.start + session_duration,
                completed=False
            )
            
            scheduled_sessions.append(session)
            
            # Update domains with new session and buffer
            buffer_before = session.start_time - task.buffer_before
            buffer_after = session.end_time + task.buffer_after
            buffer_slot = TimeSlot(buffer_before, buffer_after)
            
            task.duration -= session_duration
            if task.duration > timedelta():
                current_domain.subtract_slot(buffer_slot)
                overlap_metric = calculate_overlap_metric(current_domain, weighted_intervals)
                heapq.heappush(tasks_with_domains, (topo_rank, -overlap_metric, task, current_domain))
                print(f"Scheduled session of task {task.title} from {session.start_time.strftime('%Y-%m-%d %H:%M')} to {session.end_time.strftime('%H:%M')} ({session_duration}). Remaining duration: {task.duration}")
            else:
                print(f"Task {task.title} fully scheduled")
                remove_overlap_weighting(current_domain, weighted_intervals)
            
            new_heap = []
            while tasks_with_domains:
                rank, _, task, curr_domain = heapq.heappop(tasks_with_domains)
                curr_domain.subtract_slot(buffer_slot)
                overlap_metric = calculate_overlap_metric(curr_domain, weighted_intervals)
                heapq.heappush(new_heap, (rank, -overlap_metric, task, curr_domain))
            tasks_with_domains = new_heap
            
        return scheduled_sessions
