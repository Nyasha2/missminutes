from dataclasses import dataclass, field
import uuid

@dataclass
class Tag:
    """Represents a tag with associated constraints and metadata."""
    name: str # e.g."high-focus", "assignments", "coding"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Tag):
            return NotImplemented
        return self.id == other.id
