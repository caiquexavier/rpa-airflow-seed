"""Pydantic models for RobotOperatorSaga operations."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RobotOperatorSagaEventModel(BaseModel):
    """Model for RobotOperatorSaga events."""
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    step_id: Optional[str] = Field(None, description="Robot operator step ID")
    robot_operator_id: Optional[str] = Field(None, description="Robot operator identifier")
    occurred_at: Optional[str] = Field(None, description="Event timestamp")


class CreateRobotOperatorSagaRequest(BaseModel):
    """Request model for creating a RobotOperatorSaga."""
    saga_id: int = Field(..., description="Parent saga ID")
    robot_operator_id: str = Field(..., description="Robot operator identifier")
    data: Dict[str, Any] = Field(..., description="Saga data payload (merged from parent saga)")
    callback_path: Optional[str] = Field(None, description="Callback path for webhook")


class UpdateRobotOperatorSagaEventRequest(BaseModel):
    """Request model for updating a RobotOperatorSaga event."""
    robot_operator_saga_id: int = Field(..., description="Robot operator saga ID")
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    step_id: Optional[str] = Field(None, description="Robot operator step ID")
    robot_operator_id: Optional[str] = Field(None, description="Robot operator identifier")


class RobotOperatorSagaResponse(BaseModel):
    """Response model for robot operator saga operations."""
    robot_operator_saga_id: int = Field(..., description="Robot operator saga ID")
    saga_id: int = Field(..., description="Parent saga ID")
    current_state: str = Field(..., description="Current saga state")
    events_count: int = Field(..., description="Number of events")
    message: str = Field(..., description="Operation message")

