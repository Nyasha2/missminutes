from dataclasses import dataclass, field
from datetime import timedelta
import uuid

@dataclass
class Tag:
    """Represents a tag with associated constraints and metadata."""
    name: str # e.g."high-focus", "assignments", "coding"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # --- Constraint Fields ---

    buffer_before: timedelta | None = None
    buffer_after: timedelta | None = None
    min_session_length: timedelta | None = None
    max_session_length: timedelta | None = None
    profile_ids: set[str] = field(default_factory=set)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Tag):
            return NotImplemented
        return self.id == other.id
