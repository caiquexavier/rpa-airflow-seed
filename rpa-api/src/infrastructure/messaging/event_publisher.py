"""Event publisher - Publish domain events."""
import logging
from typing import Any

from ...domain.events.execution_events import (
    ExecutionCreated, ExecutionStarted, ExecutionCompleted, ExecutionFailed, TaskEvent
)

logger = logging.getLogger(__name__)


def publish_execution_created(event: ExecutionCreated) -> None:
    """Publish ExecutionCreated event."""
    logger.info(f"ExecutionCreated event: exec_id={event.exec_id}, rpa_key_id={event.rpa_key_id}")


def publish_execution_started(event: ExecutionStarted) -> None:
    """Publish ExecutionStarted event."""
    logger.info(f"ExecutionStarted event: exec_id={event.exec_id}, rpa_key_id={event.rpa_key_id}")


def publish_execution_completed(event: ExecutionCompleted) -> None:
    """Publish ExecutionCompleted event."""
    logger.info(f"ExecutionCompleted event: exec_id={event.exec_id}, rpa_key_id={event.rpa_key_id}")


def publish_execution_failed(event: ExecutionFailed) -> None:
    """Publish ExecutionFailed event."""
    logger.info(f"ExecutionFailed event: exec_id={event.exec_id}, rpa_key_id={event.rpa_key_id}")


def publish_task_event(event: TaskEvent) -> None:
    """Publish TaskEvent."""
    logger.info(
        f"TaskEvent: saga_id={event.saga_id}, exec_id={event.exec_id}, "
        f"task_id={event.task_id}, event_type={event.event_type}"
    )

