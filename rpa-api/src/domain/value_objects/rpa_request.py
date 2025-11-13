"""RPA Request value object."""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class RpaRequest:
    """RPA Request value object - immutable."""
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RpaRequest":
        """Create from dictionary."""
        return cls(data=data)

