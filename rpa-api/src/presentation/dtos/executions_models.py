"""Pydantic models for execution request/response validation."""
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, constr, AnyUrl, Field, model_validator
from pydantic import ConfigDict

from ...domain.entities.execution import ExecutionStatus


class SagaEventModel(BaseModel):
    """Model for SAGA events."""
    
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    task_id: Optional[str] = Field(None, description="Task ID")
    dag_id: Optional[str] = Field(None, description="DAG ID")
    occurred_at: Optional[str] = Field(None, description="Event timestamp")


class SagaModel(BaseModel):
    """Model for SAGA object."""
    
    rpa_key_id: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="RPA identifier (required, non-empty string)"
    )
    rpa_request_object: Dict[str, Any] = Field(
        ..., description="RPA request payload"
    )
    events: List[SagaEventModel] = Field(
        default_factory=list, description="List of SAGA events"
    )
    current_state: str = Field(
        default="PENDING", description="Current SAGA state"
    )


class RpaExecutionRequestModel(BaseModel):
    """Model for RPA execution requests."""
    
    saga: SagaModel = Field(..., description="SAGA object from Airflow")
    callback_url: Optional[AnyUrl] = Field(
        None, description="Optional callback URL for status updates"
    )


class RpaExecutionResponseModel(BaseModel):
    """Model for RPA execution responses."""
    
    exec_id: int = Field(..., description="Execution ID")
    rpa_key_id: str = Field(..., description="RPA identifier")
    status: str = Field(..., description="Execution status")
    message: str = Field(..., description="Status message")
    published: bool = Field(..., description="Whether message was published to queue")


class UpdateExecutionRequestModel(BaseModel):
    """Model for updating RPA execution status."""
    
    # Allow saga field but forbid other unknown fields
    model_config = ConfigDict(extra='forbid')

    exec_id: int = Field(..., description="Execution ID to update")
    rpa_key_id: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="RPA identifier (must match existing row)"
    )
    rpa_response: Dict[str, Any] = Field(
        ..., description="RPA response payload (required, can be empty object)"
    )
    status: ExecutionStatus = Field(..., description="Final execution status")
    error_message: Optional[str] = Field(
        None, description="Error message (required if status=FAIL)"
    )
    saga: Optional[Dict[str, Any]] = Field(
        None, description="Updated SAGA object from listener (optional)"
    )
    
    @model_validator(mode='after')
    def validate_error_message_required_for_fail(self):
        """Require error_message when status is FAIL."""
        if self.status == ExecutionStatus.FAIL and not self.error_message:
            raise ValueError('error_message is required when status is FAIL')
        return self

    @model_validator(mode='after')
    def validate_rpa_response_structure(self):
        """Enforce rpa_response shape depending on status.
        - SUCCESS: rpa_response must have "notas_fiscais" array with status for each
        - FAIL: rpa_response must be {"error": <non-empty string>} and error_message must equal that string
        """
        if self.status == ExecutionStatus.SUCCESS:
            if self.error_message is not None:
                raise ValueError('error_message must be null when status is SUCCESS')
            if not isinstance(self.rpa_response, dict):
                raise ValueError('rpa_response must be a dict when status is SUCCESS')
            if "notas_fiscais" not in self.rpa_response:
                raise ValueError('rpa_response must have "notas_fiscais" array when status is SUCCESS')
            if not isinstance(self.rpa_response.get("notas_fiscais"), list):
                raise ValueError('rpa_response.notas_fiscais must be an array when status is SUCCESS')
        elif self.status == ExecutionStatus.FAIL:
            if not isinstance(self.rpa_response, dict) or set(self.rpa_response.keys()) != {"error"}:
                raise ValueError('rpa_response must be {"error":"<message>"} when status is FAIL')
            err = self.rpa_response.get("error")
            if not isinstance(err, str) or not err.strip():
                raise ValueError('rpa_response.error must be a non-empty string when status is FAIL')
            if self.error_message != err:
                raise ValueError('error_message must equal rpa_response.error when status is FAIL')
        return self


class UpdateExecutionResponseModel(BaseModel):
    """Model for update execution responses mirroring request with rpa_response."""
    
    exec_id: int = Field(..., description="Execution ID")
    rpa_key_id: str = Field(..., description="RPA identifier")
    status: str = Field(..., description="Updated execution status")
    rpa_response: Dict[str, Any] = Field(..., description="Simplified response object (success or error text)")
    error_message: Optional[str] = Field(None, description="Error message text when status is FAIL")
    updated: bool = Field(True, description="Indicates the execution was updated")
