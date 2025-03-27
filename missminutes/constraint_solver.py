from dataclasses import dataclass
from datetime import datetime, timedelta
from .timedomain import TimeDomain
from .tasks import Task, Session, Event, DependencyType
import uuid
from collections import defaultdict
import heapq
from collections import deque
from portion import Interval, closed, to_string


def calculate_overlap_metric(domain: TimeDomain, domain_overlaps: TimeDomain) -> float:
    """Calculate the overlap metric for a time domain"""
    assert not domain.is_empty(), "calculate_overlap_metric: empty time domain"
    assert not domain_overlaps.is_empty(), "calculate_overlap_metric: empty domain_overlaps"
    intersection = domain_overlaps.intersection(domain)
    return intersection.total_weight_time() / intersection.total_time().total_seconds()


def sorted_slots(domain: TimeDomain, domain_overlaps: TimeDomain, max_session_length: timedelta | None) -> list[tuple[Interval, int]]:
    """Sort slots in domain by domain_overlaps. Least overlapped slots come first."""
    assert not domain.is_empty(), "sorted_slots: empty time domain"
    if max_session_length is None:
        max_session_length = domain.total_time()
    intersection = domain_overlaps.intersection(domain)
    intersection_dict = intersection.time_slots.as_dict()
    intermediate : list[tuple[Interval, int]] = sorted(intersection.time_slots.items(), key=lambda x: intersection_dict[x[0]])
    final : list[tuple[Interval, int]] = []
    for iv, v in intermediate:
        if iv.atomic:
            final.append((iv, v))
        else:
            final.extend(sorted([(atomic, v) for atomic in iv], key=lambda x: abs((x[0].upper - x[0].lower).total_seconds() - max_session_length.total_seconds())))
    return final

def apply_min_session_length_constraint(domain: TimeDomain, min_session_length: timedelta) -> None:
    """Remove all slots with duration less than min_session_length"""
    for slot in domain.time_slots:
        for atomic in slot:
            if atomic.upper - atomic.lower < min_session_length:
                domain.remove_slot(atomic.lower, atomic.upper)

@dataclass
class ConstraintSolver:
    def overlap_domains(self, domains: list[TimeDomain]) -> TimeDomain:
        """
        Breaks existing domain intervals into more granular intervals which
        are then weighted by the number of intersecting domains.
        Returns sorted dict of sub-intervals to weights.
        """
        weighted_intervals = TimeDomain()
        for domain in domains:
            weighted_intervals = weighted_intervals.add(domain)
        return weighted_intervals


    def topo_rank(self, tasks: list[Task]) -> dict[str, int]:
        """Topological sort of tasks. Returns a dict of task id to rank"""
        # Create dependency graph and in-degree count
        graph = defaultdict(set)
        in_degree = defaultdict(int)
        all_nodes = set()

        for task in tasks:
            all_nodes.add(task.id)
            for dep_id, dep_type in task.task_dependencies.items():
                if dep_type == DependencyType.AFTER:
                    graph[dep_id].add(task.id)  # Reverse edge for Kahn's algorithm
                    in_degree[task.id] += 1

        # Initialize queue with root nodes (in-degree 0), sorted for determinism
        queue = deque(sorted([node for node in all_nodes if in_degree[node] == 0]))
        ranks = {node: 0 for node in queue}

        while queue:
            node = queue.popleft()
            for neighbor in sorted(graph[node]):  # Sort for determinism
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    ranks[neighbor] = ranks[node] + 1
                    queue.append(neighbor)

        if len(ranks) != len(all_nodes):
            raise ValueError("Cycle detected in task dependencies")

        return ranks

    def presolve(self, tasks: list[Task], events: list[Event], start_date: datetime, days: int) -> tuple[TimeDomain, list[tuple[int, float, Task, TimeDomain]]]:
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
            task_domain = task_domain.difference(events_domain)
            assert not task_domain.is_empty(), f'presolve: Task "{task.title}" domain is empty after applying event constraints'
            
            for dep_id, dep_type in task.event_dependencies.items():
                if dep_type == DependencyType.AFTER:
                    task_domain.trim_left(events_map[dep_id].end_time)
                elif dep_type == DependencyType.BEFORE:
                    task_domain.trim_right(events_map[dep_id].start_time)
                elif dep_type == DependencyType.DURING:
                    task_domain = TimeDomain(task_domain.time_slots[closed(events_map[dep_id].start_time, events_map[dep_id].end_time)])
            assert task_domain.total_time() >= task.get_remaining_duration(), f'Task "{task.title}" domain ran out of time after event dependency constraint'
            
            tasks_domains.append((task, task_domain))

        
        topo_ranks = self.topo_rank(tasks)
        interval_overlaps = self.overlap_domains([domain for _, domain in tasks_domains])
        sorted_tasks_with_domains : list[tuple[int, float, Task, TimeDomain]] = []  
        for task, domain in tasks_domains:
            assert not domain.is_empty(), f'presolve: Task "{task.title}" domain is empty after applying constraints'
            overlap_metric = calculate_overlap_metric(domain, interval_overlaps)
            heapq.heappush(sorted_tasks_with_domains, (topo_ranks[task.id], -overlap_metric, task, domain))
        
        return interval_overlaps, sorted_tasks_with_domains
    
        
    def solve(self, tasks: list[Task], events: list[Event], start_date: datetime, days: int) -> list[Session]:
        """Solve scheduling problem using backtracking"""
        interval_overlaps, tasks_with_domains = self.presolve(tasks, events, start_date, days)
        
        scheduled_sessions: list[Session] = []

        print(f"Starting solve with heap size {len(tasks_with_domains)}")
        while tasks_with_domains:
            print(f"Remaining tasks to fully schedule: {len(tasks_with_domains)}")
            topo_rank, m, task, current_domain = heapq.heappop(tasks_with_domains)
            
            remaining_duration = task.get_remaining_duration()
            session_lb = min(task.min_session_length, remaining_duration)
            ideal_session_length = min(task.max_session_length or remaining_duration, remaining_duration)
            print(f"Attempting to schedule task {task.title} with ideal session length {ideal_session_length} and metric {-m}")
            
            # assert task.get_remaining_duration() >= task.min_session_length, f'Task "{task.title}" has min session length {task.min_session_length} > remaining duration {task.get_remaining_duration()}'
            
            # constraints already applied:
            #1. deadline constraint (domain doesn't go beyond deadline)
            #2. preferred window constraint (domain doesn't go beyond preferred window or is weighted by preferred window)
            #3. task dependency constraint (tasks are topo sorted)
            
            apply_min_session_length_constraint(current_domain, session_lb)
            assert current_domain.total_time() >= remaining_duration, f'Task "{task.title}" domain ran out of time after min session length constraint'
            slots = sorted_slots(current_domain, interval_overlaps, ideal_session_length)
            assert slots, f'Task "{task.title}" domain has no slots after min session length constraint'
            
            print("Available slots: ")
            for slot, v in slots:
                print(f"\t{to_string(slot, lambda x: f"{x.strftime('%a')} {x.strftime('%H:%M')}")} <{slot.upper - slot.lower}> <{v}>")
            # Try first available slot
            best_slot, _ = slots[0]
            assert best_slot.atomic, f'Best slot is not atomic: {best_slot}'
            
            session_duration = min(
                ideal_session_length,
                best_slot.upper - best_slot.lower
            ) # this intrinsically applies the max session lenth constraint
            
            session = Session(
                task_id=task.id,
                session_id=str(uuid.uuid4()),
                start_time=best_slot.lower,
                end_time=best_slot.lower + session_duration,
                completed=False
            )
            
            scheduled_sessions.append(session)
            
            # Update domains with new session and buffer
            buffer_before = session.start_time - task.buffer_before
            buffer_after = session.end_time + task.buffer_after
            
            task.duration -= session_duration
            if task.duration > timedelta():
                current_domain.remove_slot(buffer_before, buffer_after)
                overlap_metric = calculate_overlap_metric(current_domain, interval_overlaps)
                heapq.heappush(tasks_with_domains, (topo_rank, -overlap_metric, task, current_domain))
                print(f"Scheduled session of task {task.title} from {session.start_time.strftime('%a %H:%M')} to {session.end_time.strftime('%a %H:%M')} ({session_duration}). Remaining duration: {task.duration}")
            else:
                print(f"Scheduled session of task {task.title} from {session.start_time.strftime('%a %H:%M')} to {session.end_time.strftime('%a %H:%M')} ({session_duration}). Remaining duration: {task.duration}")
                print(f"Task {task.title} fully scheduled")
                interval_overlaps = interval_overlaps.subtract(current_domain) # subtract overlap weighting
            
            new_heap = []
            while tasks_with_domains:
                rank, _, other_task, curr_domain = heapq.heappop(tasks_with_domains)
                curr_domain.remove_slot(buffer_before, buffer_after)
                assert curr_domain.total_time() >= other_task.get_remaining_duration(), f'Task "{other_task.title}" domain ran out of time after session for {task.title} scheduled'
                overlap_metric = calculate_overlap_metric(curr_domain, interval_overlaps)
                heapq.heappush(new_heap, (rank, -overlap_metric, other_task, curr_domain))
            tasks_with_domains = new_heap
            
        return scheduled_sessions
