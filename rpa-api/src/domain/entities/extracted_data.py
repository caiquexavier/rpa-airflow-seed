"""ExtractedData entity - Domain model for GPT-extracted metadata."""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class ExtractedData:
    """ExtractedData entity - immutable domain model."""
    id: int
    saga_id: int
    identifier: Optional[str]
    identifier_code: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime

