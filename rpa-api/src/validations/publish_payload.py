"""Pydantic validation models for publish payload."""
from typing import Any, Dict

from pydantic import BaseModel, Field, constr, ConfigDict


class PublishPayload(BaseModel):
    """Validation model for publish payload with rpa-id field alias."""
    
    rpa_id: constr(min_length=1) = Field(..., alias="rpa-id")
    
    model_config = ConfigDict(
        # Allow extra fields in the payload
        extra="allow",
        # Allow population by field name and alias
        populate_by_name=True,
        # Use alias for serialization
        by_alias=True
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary preserving the original field names.
        
        Returns:
            Dict containing the payload with original field names
        """
        return self.model_dump(by_alias=True)
