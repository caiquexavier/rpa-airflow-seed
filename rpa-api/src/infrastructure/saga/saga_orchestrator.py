"""SAGA orchestrator - Coordinates workflow execution."""
import logging
from typing import Optional, Callable
from datetime import datetime

from ...domain.entities.saga import Saga, SagaState
from ...domain.events.execution_events import TaskEvent
from ...application.use_cases.saga_use_cases import (
    create_saga, add_saga_event, get_saga
)
from ...application.commands.create_saga_command import CreateSagaCommand
from ...application.commands.add_saga_event_command import AddSagaEventCommand
from ...application.queries.get_saga_query import GetSagaQuery

logger = logging.getLogger(__name__)


class SagaOrchestrator:
    """SAGA orchestrator - Manages workflow state and events."""
    
    def __init__(
        self,
        save_saga_fn: Callable[[Saga], int],
        get_saga_fn: Callable[[int], Optional[Saga]],
        save_event_fn: Callable[[TaskEvent], None],
        publish_event_fn: Callable[[TaskEvent], None]
    ):
        self.save_saga_fn = save_saga_fn
        self.get_saga_fn = get_saga_fn
        self.save_event_fn = save_event_fn
        self.publish_event_fn = publish_event_fn
    
    def start_saga(
        self,
        rpa_key_id: str,
        data: dict
    ) -> int:
        """
        Start a new SAGA.
        
        Args:
            rpa_key_id: RPA key identifier
            data: Saga data payload
        
        Returns:
            saga_id
        """
        command = CreateSagaCommand(
            rpa_key_id=rpa_key_id,
            data=data
        )
        
        return create_saga(
            command=command,
            save_saga=self.save_saga_fn,
            publish_event=self.publish_event_fn
        )
    
    def record_task_event(
        self,
        saga_id: int,
        task_id: str,
        dag_id: str,
        event_type: str,
        event_data: dict
    ) -> Saga:
        """
        Record an event for a task in the SAGA.
        
        Args:
            saga_id: Saga ID
            task_id: DAG task identifier
            dag_id: DAG identifier
            event_type: Event type
            event_data: Event data
        
        Returns:
            Updated saga
        """
        command = AddSagaEventCommand(
            saga_id=saga_id,
            event_type=event_type,
            event_data=event_data,
            task_id=task_id,
            dag_id=dag_id
        )
        
        return add_saga_event(
            command=command,
            get_saga=self.get_saga_fn,
            save_saga=self.save_saga_fn,
            save_event=self.save_event_fn
        )
    
    
    def get_events_for_task(self, saga_id: int, task_id: str) -> list[TaskEvent]:
        """Get all events for a specific task."""
        saga = self.get_saga_fn(saga_id)
        if not saga:
            return []
        return saga.get_events_by_task(task_id)

