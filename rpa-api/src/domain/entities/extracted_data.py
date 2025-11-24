"""ExtractedData entity - Domain model for GPT-extracted metadata."""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass(frozen=True)
class ExtractedData:
    """ExtractedData entity - immutable domain model."""
    id: int
    saga_id: int
    metadata: Dict[str, Any]
    created_at: datetime

