from typing import List, Optional
from datetime import datetime
from .json_store import JsonStore
from ..models.session import Session

class SessionStore:
    """Manages storage and retrieval of task sessions"""
    
    def __init__(self):
        self.store = JsonStore()
        
    def save_session(self, session: Session):
        """Save a session"""
        self.store.save(f"sessions/{session.task_id}/{session.start_time.isoformat()}", session)
        
    def get_sessions(self, task_id: str) -> List[Session]:
        """Get all sessions for a task"""
        return self.store.load(f"sessions/{task_id}") or []
        
    def get_sessions_in_range(self, start: datetime, end: datetime) -> List[Session]:
        """Get all sessions within a time range"""
        all_sessions = []
        for task_sessions in self.store.load("sessions").values():
            all_sessions.extend([
                s for s in task_sessions 
                if s.start_time >= start and s.end_time <= end
            ])
        return sorted(all_sessions, key=lambda s: s.start_time) 