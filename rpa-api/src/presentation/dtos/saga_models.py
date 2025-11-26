"""Pydantic models for Saga operations."""
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class SagaEventModel(BaseModel):
    """Model for SAGA events."""
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    task_id: Optional[str] = Field(None, description="Task ID")
    dag_id: Optional[str] = Field(None, description="DAG ID")
    dag_run_id: Optional[str] = Field(None, description="DAG run ID")
    execution_date: Optional[str] = Field(None, description="Execution date/timestamp")
    try_number: Optional[int] = Field(None, description="Task try number")
    operator_type: Optional[str] = Field(None, description="Operator type (e.g., PythonOperator, RobotFrameworkOperator)")
    operator_id: Optional[str] = Field(None, description="Operator identifier")
    operator_params: Optional[Dict[str, Any]] = Field(None, description="Operator parameters")
    occurred_at: Optional[str] = Field(None, description="Event timestamp")


class DAGTaskConfig(BaseModel):
    """Model for DAG task configuration."""
    task_id: str = Field(..., description="Task ID")
    task_type: str = Field(..., description="Task type (e.g., PythonOperator, RobotFrameworkOperator)")
    operator_class: Optional[str] = Field(None, description="Operator class name")
    dependencies: Optional[List[str]] = Field(default_factory=list, description="List of task IDs this task depends on")
    robot_test_file: Optional[str] = Field(None, description="Robot Framework test file for RobotFrameworkOperator")
    rpa_key_id: Optional[str] = Field(None, description="RPA key ID for RobotFrameworkOperator")


class DAGConfig(BaseModel):
    """Model for DAG configuration."""
    dag_id: str = Field(..., description="DAG ID")
    tasks: List[DAGTaskConfig] = Field(..., description="List of tasks in the DAG")


class CreateSagaRequest(BaseModel):
    """Request model for creating a Saga."""
    rpa_key_id: str = Field(..., description="RPA key identifier")
    data: Dict[str, Any] = Field(..., description="Saga data payload")
    dag_id: Optional[str] = Field(None, description="DAG ID")
    dag_run_id: Optional[str] = Field(None, description="DAG run ID")
    execution_date: Optional[str] = Field(None, description="Execution date/timestamp")
    task_id: Optional[str] = Field(None, description="Task ID for start event")
    operator_type: Optional[str] = Field(None, description="Operator type for start event")
    operator_id: Optional[str] = Field(None, description="Operator identifier for start event")
    operator_params: Optional[Dict[str, Any]] = Field(None, description="Operator parameters for start event")
    initial_events: Optional[List[SagaEventModel]] = Field(
        default_factory=list,
        description="Initial events from Airflow (deprecated, use dag_config instead)"
    )
    dag_config: Optional[DAGConfig] = Field(
        None,
        description="DAG configuration to build complete SAGA structure upfront"
    )


class UpdateSagaEventRequest(BaseModel):
    """Request model for updating a Saga event."""
    saga_id: int = Field(..., description="Saga ID")
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    task_id: Optional[str] = Field(None, description="Task ID")
    dag_id: Optional[str] = Field(None, description="DAG ID")
    dag_run_id: Optional[str] = Field(None, description="DAG run ID")
    execution_date: Optional[str] = Field(None, description="Execution date/timestamp")
    try_number: Optional[int] = Field(None, description="Task try number")
    operator_type: Optional[str] = Field(None, description="Operator type (e.g., PythonOperator, RobotFrameworkOperator)")
    operator_id: Optional[str] = Field(None, description="Operator identifier")
    operator_params: Optional[Dict[str, Any]] = Field(None, description="Operator parameters")


# TODO: Re-enable after refactoring finishes - Robot execution endpoint needs to be fully implemented
# class RequestRobotExecutionRequest(BaseModel):
#     """Request model for robot execution."""
#     saga_id: int = Field(..., description="Saga ID")
#     callback_path: Optional[str] = Field(None, description="Callback path for webhook")
#     saga: Optional[Dict[str, Any]] = Field(None, description="Saga object (optional, for backward compatibility)")


class SagaResponse(BaseModel):
    """Response model for saga operations."""
    saga_id: int = Field(..., description="Saga ID")
    current_state: str = Field(..., description="Current saga state")
    events_count: int = Field(..., description="Number of events")
    message: str = Field(..., description="Operation message")


class UpdateSagaDataRequest(BaseModel):
    """Request model for updating Saga data payload."""
    saga_id: int = Field(..., description="Saga ID")
    data: Dict[str, Any] = Field(..., description="Updated saga data payload")

