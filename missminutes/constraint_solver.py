from dataclasses import dataclass
from datetime import datetime, timedelta
from .timedomain import TimeDomain
from .tasks import Task, Session, Event, DependencyType
import uuid
from collections import defaultdict, deque
import heapq
from portion import Interval, closed, to_string, empty
from tabulate import tabulate


# --- Duration Rounding Helpers ---
FIVE_MINUTES = timedelta(minutes=5)

def round_timedelta_down(td: timedelta, interval: timedelta = FIVE_MINUTES) -> timedelta:
    """Rounds a timedelta down to the nearest interval (default 5 minutes)."""
    if td < timedelta(0):
        return timedelta(0) # Cannot have negative duration
    total_seconds = td.total_seconds()
    interval_seconds = interval.total_seconds()
    rounded_seconds = (total_seconds // interval_seconds) * interval_seconds
    return timedelta(seconds=rounded_seconds)

def round_timedelta_up(td: timedelta, interval: timedelta = FIVE_MINUTES) -> timedelta:
    """Rounds a timedelta up to the nearest interval (default 5 minutes)."""
    if td <= timedelta(0):
        return timedelta(0) # Or perhaps return interval if non-zero needed?
    total_seconds = td.total_seconds()
    interval_seconds = interval.total_seconds()
    # Use ceiling division logic
    rounded_seconds = ((total_seconds + interval_seconds - 1) // interval_seconds) * interval_seconds
    # Alternative: Check if perfectly divisible, otherwise add interval and round down
    # if total_seconds % interval_seconds == 0:
    #     rounded_seconds = total_seconds
    # else:
    #     rounded_seconds = ((total_seconds // interval_seconds) + 1) * interval_seconds
    return timedelta(seconds=rounded_seconds)

# --- Custom Exception ---
class SchedulingError(Exception):
    """Custom exception for scheduling failures."""
    pass

def calculate_overlap_metric(domain: TimeDomain, domain_overlaps: TimeDomain) -> float:
    assert not domain.is_empty(), "calculate_overlap_metric: empty time domain"
    assert not domain_overlaps.is_empty(), "calculate_overlap_metric: empty domain_overlaps"

    intersection = domain_overlaps.intersection(domain)
    weighted_sum = 0
    total_time = 0
    due_date = domain.time_slots.domain().upper
    
    for interval, weight in intersection.time_slots.items():
        for atomic in interval:
            interval_duration = (atomic.upper - atomic.lower).total_seconds()
            # Exponential decay as we get further from deadline
            deadline_factor = 1 # deadline factors dont seem to have an effect, maybe already sufficiently captured by overlap
            # deadline_factor = 2 ** (-max(0, (due_date -
            # interval.upper).total_seconds() / (24*3600)))
            weighted_sum += weight * interval_duration * deadline_factor
            total_time += interval_duration
    return weighted_sum / total_time
        
    # """Calculate the overlap metric for a time domain""" assert not
    # domain.is_empty(), "calculate_overlap_metric: empty time domain" assert
    # not domain_overlaps.is_empty(), "calculate_overlap_metric: empty
    # domain_overlaps" intersection = domain_overlaps.intersection(domain)
    # return intersection.total_weight_time() /
    # intersection.total_time().total_seconds()

def calculate_pressure_metric(domain: TimeDomain, domain_overlaps: TimeDomain, task_duration: timedelta) -> float:
    """
    Calculate scheduling pressure metric that combines overlap and flexibility
    Higher pressure = higher priority for scheduling
    
    pressure = average_overlap * (task_duration / domain_size)
    
    This can be interpreted as: "average number of competing tasks per available
    slot"
    """
    overlap_metric = calculate_overlap_metric(domain, domain_overlaps)
    flexibility_ratio = domain.total_time().total_seconds() / task_duration.total_seconds()
    return overlap_metric / flexibility_ratio


def sorted_slots(domain: TimeDomain, domain_overlaps: TimeDomain, task: Task, ideal_length: timedelta) -> list[tuple[Interval, int]]:
    """Sort slots using multiple criteria"""
    intersection = domain_overlaps.intersection(domain)
    slots_with_scores = []
    
    table_data = []
    
    for interval in intersection.time_slots.domain():
        for atomic in interval:
            duration = atomic.upper - atomic.lower
            overlap_weight = 0
            
            for iv, weight in intersection.time_slots[atomic].items():
                overlap = atomic.intersection(iv)
                overlap_weight += weight * (overlap.upper - overlap.lower).total_seconds()
                
            overlap_weight /= duration.total_seconds()
            
            # Multiple scoring factors:
            overlap_score = overlap_weight 
            length_fit_score = abs((duration.total_seconds() - ideal_length.total_seconds()) / ideal_length.total_seconds())
            deadline_proximity = (task.due - atomic.upper).total_seconds()
            deadline_proximity_score = 1 / max(1, deadline_proximity/(24*3600))
            
            # Composite score (weights can be tuned)
            slot_score = (
                overlap_score * 0.4 +
                length_fit_score * 0.3 +
                deadline_proximity_score * 1
            )

            
            slots_with_scores.append((atomic, slot_score))
            table_data.append([
                atomic.lower.strftime("%a %m/%d %I:%M%p"), 
                atomic.upper.strftime("%a %m/%d %I:%M%p"), 
                duration, 
                overlap_score, 
                length_fit_score, 
                deadline_proximity_score, 
                slot_score
            ])
            
    headers = ["Start", "End", "Duration", "Overlap", "Length Fit", "Deadline Proximity", "Score"]
    sorted_table_data = sorted(table_data, key=lambda x: x[6])
    print(f"Slots for task {task.title}:")
    print(tabulate(sorted_table_data, headers=headers, tablefmt="github"))
    return sorted(slots_with_scores, key=lambda x: x[1])

def apply_min_session_length_constraint(domain: TimeDomain, min_session_length: timedelta) -> None:
    """Remove all slots with duration less than min_session_length"""
    for slot in domain.time_slots:
        for atomic in slot:
            if atomic.upper - atomic.lower < min_session_length:
                domain.remove_slot(atomic.lower, atomic.upper)

def find_best_compatible_session(
    task: Task,
    slot: Interval,
    other_tasks_with_domains: list[tuple[int, float, Task, TimeDomain]]
) -> Interval | None:
    """
    Finds the best compatible session interval within a given atomic slot for a task,
    ensuring it doesn't make any other task unschedulable.

    Prioritizes maximum allowed duration, then minimum required duration.

    Args:
        task: The task to schedule a session for.
        slot: The atomic candidate time interval for the session.
        other_tasks_with_domains: List of tuples representing the other tasks still
                                  in the scheduling queue, including their domains.

    Returns:
        The core interval (without buffers) of the best compatible session found,
        or None if no compatible session (even minimum duration) can be found.
    """
    assert slot.atomic, "Input slot must be atomic"

    start_time = slot.lower
    available_duration = slot.upper - start_time
    task_remaining = task.get_remaining_duration()

    # 1. Determine Min/Max Session Duration Bounds for this slot (Aligned to 5 min)
    # Effective minimum: task's min_session OR remaining duration if less
    min_duration_raw = min(task.min_session_length, task_remaining)
    # Round UP to ensure minimum requirement is met or exceeded
    effective_min_duration = round_timedelta_up(min_duration_raw)

    if effective_min_duration <= timedelta(0):
        effective_min_duration = FIVE_MINUTES # Ensure at least one 5-min block if possible

    # Max possible duration in this slot, respecting task limits and availability
    max_duration_raw = min(
        task.max_session_length or timedelta(days=365*100), # Large default if no max
        task_remaining,
        available_duration
    )
    # Round DOWN to ensure we don't exceed limits
    max_possible_duration = round_timedelta_down(max_duration_raw)

    # Cannot schedule if max possible (rounded down) is less than effective min (rounded up)
    if max_possible_duration < effective_min_duration:
        # print(f"      Debug Slot {slot}: Max possible duration ({max_possible_duration}) < Min effective ({effective_min_duration}) after 5min rounding. Skipping.")
        return None

    # 2. Define the Compatibility Check Function
    def is_duration_compatible(duration: timedelta) -> bool:
        """Checks if scheduling a session of 'duration' is compatible with all other tasks."""
        # Add a small tolerance to prevent issues with floating point precision near boundaries
        if duration <= timedelta(microseconds=1): # Invalid duration (use tolerance)
             return False
        # Check if end time slightly exceeds slot boundary due to precision
        if start_time + duration > slot.upper + timedelta(microseconds=1):
            return False

        session_core = closed(start_time, start_time + duration)
        session_buffered = closed(start_time - task.buffer_before,
                                  start_time + duration + task.buffer_after)

        for _, _, other_task, other_domain in other_tasks_with_domains:
            # Calculate slack for the other task
            other_remaining = other_task.get_remaining_duration()
            other_available = other_domain.total_time()
            slack = other_available - other_remaining

            if slack < timedelta(0):
                 pass # Let the cost check handle it

            intersection_slots = other_domain.time_slots[session_buffered]
            intersection_with_other = TimeDomain(intersection_slots)
            cost = intersection_with_other.total_time() if not intersection_with_other.is_empty() else timedelta(0)


            # Check if the cost exceeds the slack (allow for small tolerance)
            tolerance = timedelta(microseconds=1)
            if cost > slack + tolerance:
                 # print(f"      Debug Slot {slot} Duration {duration}: Incompatible with {other_task.title}. Cost ({cost}) > Slack ({slack})")
                return False # This duration makes other_task unschedulable

        # If we went through all other tasks and none conflicted
        # print(f"      Debug Slot {slot} Duration {duration}: Compatible with all other tasks.")
        return True

    # 3. Binary Search for the Best Compatible Duration
    best_compatible_duration: timedelta | None = None
    low = effective_min_duration
    high = max_possible_duration

    # Check if the minimum duration is even possible before starting search
    if not is_duration_compatible(low):
        # print(f"      Debug Slot {slot}: Minimum 5min duration {low} is not compatible.")
        return None

    # Perform binary search for ~10 iterations (adjust as needed for precision/performance)
    # Using iterations avoids potential infinite loops with timedelta precision
    for _ in range(10):
        if high < low:
             break

        # Calculate midpoint in terms of 5-minute intervals
        low_intervals = low.total_seconds() // FIVE_MINUTES.total_seconds()
        high_intervals = high.total_seconds() // FIVE_MINUTES.total_seconds()
        mid_intervals = low_intervals + (high_intervals - low_intervals) // 2

        # Convert back to timedelta
        mid_duration = timedelta(minutes=mid_intervals * 5)

        # Ensure mid_duration doesn't fall below the effective minimum due to integer division
        if mid_duration < effective_min_duration:
            mid_duration = effective_min_duration

        # Check if mid_duration exceeds high (can happen if high was not a multiple of 5 min initially)
        if mid_duration > max_possible_duration:
            # If midpoint exceeds max, try the max itself if it's compatible
            if is_duration_compatible(max_possible_duration):
                best_compatible_duration = max_possible_duration
            break # No need to search further up

        if is_duration_compatible(mid_duration):
            # This duration is compatible, store it and try larger durations
            best_compatible_duration = mid_duration
            # Move low up to the next 5-minute interval
            low = mid_duration + FIVE_MINUTES
        else:
            # This duration is not compatible, move high down to the previous 5-minute interval
            high = mid_duration - FIVE_MINUTES

    if best_compatible_duration:
        # Ensure the final duration is definitely a multiple of 5 mins and within bounds
        final_duration = round_timedelta_down(best_compatible_duration) # Should already be, but enforce
        final_duration = max(final_duration, effective_min_duration) # Ensure minimum met
        final_duration = min(final_duration, max_possible_duration) # Ensure maximum respected

        # Double check compatibility of the final chosen duration
        if final_duration > timedelta(0) and is_duration_compatible(final_duration):
             # print(f"      Debug Slot {slot}: Found best 5min compatible duration {final_duration} via binary search.")
             return closed(start_time, start_time + final_duration)
        else:
             # This might happen if rounding/bounds checks resulted in an incompatible final duration
             # print(f"      Debug Slot {slot}: Final duration {final_duration} check failed.")
             return None
    else:
        # This case implies even the effective_min_duration was not compatible.
        # print(f"      Debug Slot {slot}: Binary search failed to find any 5min compatible duration >= {effective_min_duration}.")
        return None


@dataclass
class ConstraintSolver:
    def overlap_domains(self, domains: list[TimeDomain]) -> TimeDomain:
        """
        Breaks existing domain intervals into more granular intervals which are
        then weighted by the number of intersecting domains. Returns sorted dict
        of sub-intervals to weights.
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
        """Presolving step to prune task domains and sort them by dependency and
        overlap"""
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
            pressure_score = calculate_pressure_metric(domain, interval_overlaps, task.get_remaining_duration())
            
            heapq.heappush(sorted_tasks_with_domains, (topo_ranks[task.id], -pressure_score, task, domain))
        
        table_data = []

        for topo_rank, neg_pressure_score, task, domain in sorted_tasks_with_domains:
            overlap_metric = calculate_overlap_metric(domain, interval_overlaps)
            domain_size = domain.total_time()
            remaining_duration = task.get_remaining_duration()
            domain_ratio = domain_size / remaining_duration
            due_in = task.due - start_date
            table_data.append([task.title, topo_rank, -neg_pressure_score, overlap_metric, domain_ratio, remaining_duration, due_in])

        headers = ["Task", "TopoRank", "Pressure", "Avg Overlap", "Domain:Duration", "Duration", "Due"]
        print(tabulate(table_data, headers=headers, tablefmt="github"))
        print("Finished presolve")
        return interval_overlaps, sorted_tasks_with_domains
    
        
    def solve(self, tasks: list[Task], events: list[Event], start_date: datetime, days: int) -> list[Session]:
        """Solve scheduling problem using backtracking"""
        interval_overlaps, tasks_with_domains = self.presolve(tasks, events, start_date, days)
        
        scheduled_sessions: list[Session] = []

        print(f"Starting solve with heap size {len(tasks_with_domains)}")
        while tasks_with_domains:
            topo_rank, rank, task, current_domain = heapq.heappop(tasks_with_domains)
            
            remaining_duration = task.get_remaining_duration()
            session_duration_lb = min(task.min_session_length, remaining_duration) # lower bound
            session_duration_ub = min(task.max_session_length or remaining_duration, remaining_duration) # upper bound 
            
            # constraints already applied:
            #1. deadline constraint (domain doesn't go beyond deadline)
            #2. preferred window constraint (domain doesn't go beyond preferred
            #   window or is weighted by preferred window)
            #3. task dependency constraint (tasks are topo sorted)
            
            apply_min_session_length_constraint(current_domain, session_duration_lb)
            # assert current_domain.total_time() >= remaining_duration, f'Task "{task.title}" domain ran out of time after min session length constraint'
            slots = sorted_slots(current_domain, interval_overlaps, task, session_duration_ub) 
            # POSSIBLE BUG: if task has no defined max_session_length, ideal_session_duration is very long so sorting may be off (but we do have a default)
            
            assert slots, f'Task "{task.title}" domain has no slots after min session length constraint'
            
            scheduled_session_interval = None
            # Iterate through the sorted candidate slots for the current task to select best slot
            for slot, _ in slots:
                assert slot.atomic, f'Best slot is not atomic: {slot}'
                print(f"Trying slot {slot.lower.strftime('%a %H:%M')} - {slot.upper.strftime('%a %H:%M')} for task '{task.title}'")

                # Use the new helper function to find the best compatible session interval
                # Pass the current state of the heap (other tasks and their domains)
                temp_heap = list(tasks_with_domains) # Check against current state of the heap
                best_session_interval = find_best_compatible_session(task, slot, temp_heap)

                if best_session_interval:
                    print(f"  Found compatible session: {best_session_interval.lower.strftime('%H:%M')} - {best_session_interval.upper.strftime('%H:%M')}")
                    scheduled_session_interval = best_session_interval
                    break # Found a working slot and duration, stop iterating through slots
                else:
                    # print("  Slot not compatible with all other tasks.") # Debug
                    # Continue to the next slot in the 'slots' list
                    pass # Explicitly continue checking slots

            # After checking all slots for the task:
            if not scheduled_session_interval:
                # --- MODIFIED BEHAVIOR: Warn instead of raising error ---
                print(f"\nWARN: Could not find any compatible slot for task '{task.title}' (remaining: {task.get_remaining_duration()}). Skipping further attempts for this task.")
                # Add task to a list for final reporting (optional, can also check remaining durations later)
                # failed_tasks.append(task) # Example if needed
                # Do NOT push the task back onto the heap, just continue to the next task
                print()
                continue # Skip to the next iteration of the main while loop
                # --- END MODIFICATION ---

            # --- Session Creation and Updates (Only if a session was found) ---
            session_start_time = scheduled_session_interval.lower
            session_end_time = scheduled_session_interval.upper
            actual_session_duration = session_end_time - session_start_time

            session = Session(
                task_id=task.id,
                session_id=str(uuid.uuid4()),
                start_time=session_start_time,
                end_time=session_end_time,
                completed=False
            )
            
            scheduled_sessions.append(session)
            
            # Update task duration
            task.duration -= actual_session_duration # Use the actual duration scheduled
            
            # Define the interval to remove from other domains (including buffers)
            buffer_before = session.start_time - task.buffer_before
            buffer_after = session.end_time + task.buffer_after
            removal_interval = closed(buffer_before, buffer_after)

            if task.duration > timedelta(microseconds=1): # Use small tolerance for float precision
                # Task not finished, update its domain and push back onto heap
                current_domain.remove_slot_interval(removal_interval)
                assert not current_domain.is_empty(), f"Task '{task.title}' domain became empty after scheduling session {session.session_id}"
                # Recalculate pressure metric AFTER removing the slot
                pressure_metric = calculate_pressure_metric(current_domain, interval_overlaps, task.get_remaining_duration())
                heapq.heappush(tasks_with_domains, (topo_rank, -pressure_metric, task, current_domain))
                print(f"Scheduled session from {session.start_time.strftime('%a %H:%M')} to {session.end_time.strftime('%a %H:%M')} ({actual_session_duration}). Remaining duration: {task.duration}")
            else:
                # Task finished
                print(f"Scheduled session from {session.start_time.strftime('%a %H:%M')} to {session.end_time.strftime('%a %H:%M')} ({actual_session_duration}). Remaining duration: {task.duration}")
                print(f"Task {task.title} fully scheduled")
                # Update overlaps: remove the finished task's entire domain contribution
                interval_overlaps = interval_overlaps.subtract(current_domain) 
            print()
            
            # Update domains of *all other* tasks by removing the scheduled interval + buffers
            new_heap = []
            while tasks_with_domains:
                # Use pop to modify the heap directly is complex due to priority updates. Rebuild it.
                other_topo_rank, other_neg_pressure, other_task, other_domain = heapq.heappop(tasks_with_domains)
                
                # --- FIX: Skip updating the domain of the task that was just scheduled ---
                if other_task.id == task.id:
                    # If the task wasn't finished, it's already been updated and pushed
                    # onto the new_heap indirectly via the earlier heappush. Add it here
                    # explicitly to ensure it's in the final heap if it wasn't finished.
                    # However, the logic before this loop already handles pushing it back if needed.
                    # We just need to ensure it's part of the final list.
                    # Let's push it onto the new_heap correctly, reusing its calculated pressure.
                    # NOTE: This assumes the `task` object reference is the same and its
                    #       `current_domain` was correctly updated earlier.
                    # The push back happens *before* this loop (lines 476-480) IF the task is not finished.
                    # So, we just need to skip the processing here.
                    heapq.heappush(new_heap, (other_topo_rank, other_neg_pressure, other_task, other_domain))
                    continue # Skip the rest of the loop for this task
                # --- END FIX ---

                original_total_time = other_domain.total_time()
                other_domain.remove_slot_interval(removal_interval)
                
                # Check if the other task still has enough time
                if other_domain.total_time() < other_task.get_remaining_duration():
                     # This should ideally not happen if the consistency check was correct
                     raise SchedulingError(f'FATAL: Task "{other_task.title}" ({other_task.get_remaining_duration()}) domain ran out of time ({other_domain.total_time()}) after session for "{task.title}" was scheduled in interval {removal_interval}. Original time: {original_total_time}')
                
                # Recalculate pressure metric for the updated domain
                new_pressure_metric = calculate_pressure_metric(other_domain, interval_overlaps, other_task.get_remaining_duration())
                heapq.heappush(new_heap, (other_topo_rank, -new_pressure_metric, other_task, other_domain))
            
            tasks_with_domains = new_heap # Replace old heap with the updated one
            
        # --- Final Reporting of Underscheduled Tasks ---
        print("\n--- Scheduling Complete ---")
        underscheduled_summary = []
        # Need the original list of tasks to check final remaining durations
        # Assuming the input 'tasks' list holds the objects whose durations were updated
        for task in tasks: 
            remaining = task.get_remaining_duration()
            if remaining > timedelta(microseconds=1): # Check with tolerance
                underscheduled_summary.append(f"  - Task '{task.title}' (ID: {task.id}): Underscheduled by {remaining}")

        if underscheduled_summary:
            print("WARNING: Some tasks were underscheduled:")
            for warning in underscheduled_summary:
                print(warning)
        else:
            print("All tasks scheduled successfully.")
            
        # Optionally, return underscheduling info alongside sessions
        # underscheduled_info = {task.id: task.get_remaining_duration() for task in tasks if task.get_remaining_duration() > timedelta(microseconds=1)}
        # return scheduled_sessions, underscheduled_info
            
        return scheduled_sessions
    


