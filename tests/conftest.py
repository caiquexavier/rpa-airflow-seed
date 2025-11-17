"""Pytest configuration and shared fixtures."""
import sys
from pathlib import Path

# Add source directories to Python path
# We add the parent directories so relative imports work correctly
# IMPORTANT: rpa-api must be first to avoid config module conflicts
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "rpa-api"))
sys.path.insert(1, str(project_root / "rpa-listener"))
sys.path.insert(2, str(project_root / "airflow"))

import pytest
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from unittest.mock import Mock, MagicMock

from src.domain.entities.execution import Execution, ExecutionStatus
from src.domain.entities.saga import Saga, SagaState, SagaEvent


@pytest.fixture
def sample_datetime() -> datetime:
    """Provide a fixed datetime for testing."""
    return datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def sample_rpa_request() -> Dict[str, Any]:
    """Provide a sample RPA request payload."""
    return {
        "dt_list": [
            {"dt_id": "DT001", "notas_fiscais": ["NF001", "NF002"]},
            {"dt_id": "DT002", "notas_fiscais": ["NF003"]}
        ]
    }


@pytest.fixture
def sample_execution(sample_datetime: datetime, sample_rpa_request: Dict[str, Any]) -> Execution:
    """Provide a sample Execution entity."""
    return Execution(
        exec_id=1,
        rpa_key_id="rpa_protocolo_devolucao",
        exec_status=ExecutionStatus.PENDING,
        rpa_request=sample_rpa_request,
        rpa_response=None,
        error_message=None,
        callback_url="http://example.com/callback",
        created_at=sample_datetime,
        updated_at=sample_datetime,
        finished_at=None
    )


@pytest.fixture
def sample_saga(sample_datetime: datetime, sample_rpa_request: Dict[str, Any]) -> Saga:
    """Provide a sample Saga entity."""
    return Saga(
        saga_id=1,
        exec_id=1,
        rpa_key_id="rpa_protocolo_devolucao",
        rpa_request_object=sample_rpa_request,
        current_state=SagaState.PENDING,
        events=[],
        created_at=sample_datetime,
        updated_at=sample_datetime
    )


@pytest.fixture
def sample_saga_event(sample_datetime: datetime) -> SagaEvent:
    """Provide a sample SagaEvent."""
    return SagaEvent(
        event_type="TaskCompleted",
        event_data={"status": "SUCCESS"},
        task_id="test_task",
        dag_id="test_dag",
        occurred_at=sample_datetime
    )


@pytest.fixture
def mock_save_execution() -> Callable[[Execution], int]:
    """Mock function for saving execution."""
    def _save(execution: Execution) -> int:
        return execution.exec_id if execution.exec_id > 0 else 1
    return _save


@pytest.fixture
def mock_get_execution(sample_execution: Execution) -> Callable[[int], Optional[Execution]]:
    """Mock function for getting execution."""
    def _get(exec_id: int) -> Optional[Execution]:
        if exec_id == sample_execution.exec_id:
            return sample_execution
        return None
    return _get


@pytest.fixture
def mock_save_saga() -> Callable[[Saga], int]:
    """Mock function for saving saga."""
    def _save(saga: Saga) -> int:
        return saga.saga_id if saga.saga_id > 0 else 1
    return _save


@pytest.fixture
def mock_get_saga(sample_saga: Saga) -> Callable[[int], Optional[Saga]]:
    """Mock function for getting saga."""
    def _get(saga_id: int) -> Optional[Saga]:
        if saga_id == sample_saga.saga_id:
            return sample_saga
        return None
    return _get


@pytest.fixture
def mock_publish_event() -> Callable[[Any], None]:
    """Mock function for publishing events."""
    return Mock()


@pytest.fixture
def mock_publish_message() -> Callable[[dict], bool]:
    """Mock function for publishing messages."""
    def _publish(message: dict) -> bool:
        return True
    return _publish


@pytest.fixture
def mock_save_event() -> Callable[[Any], None]:
    """Mock function for saving events."""
    return Mock()

