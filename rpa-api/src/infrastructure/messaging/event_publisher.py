"""Event publisher - Publish and store domain events."""
import logging

from ...domain.events.execution_events import TaskEvent

logger = logging.getLogger(__name__)


def publish_task_event(event: TaskEvent) -> None:
    """Publish TaskEvent."""
    logger.info(
        f"TaskEvent: saga_id={event.saga_id}, "
        f"task_id={event.task_id}, event_type={event.event_type}"
    )

