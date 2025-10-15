"""Pydantic validation models for request payloads."""
from typing import Any, Dict

from pydantic import BaseModel, constr, AnyUrl, ConfigDict


class RpaRequestModel(BaseModel):
    """Strict validation model for RPA execution requests."""
    
    rpa_key_id: constr(strip_whitespace=True, min_length=1)  # Required, non-empty string
    callback_url: AnyUrl | None = None  # Optional, must be valid URL if provided
    rpa_request: Dict[str, Any] | None = None  # Optional, must be object if provided
    
    model_config = ConfigDict(extra="forbid")  # Reject unknown fields
