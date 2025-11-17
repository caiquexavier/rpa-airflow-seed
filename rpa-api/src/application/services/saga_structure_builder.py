"""Saga structure builder - Builds complete SAGA structure with all events upfront."""
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from ...domain.entities.saga import SagaEvent
from .dag_parser import DAGStructure, DAGTask, parse_dag_structure, build_task_execution_order
from .robot_parser import RobotTestStructure, parse_robot_file, find_robot_file

logger = logging.getLogger(__name__)


def build_complete_saga_structure(
    dag_config: Dict[str, Any],
    rpa_key_id: str,
    robots_base_path: str = "rpa-robots",
    occurred_at: Optional[datetime] = None,
    find_robot_file_fn: Optional[Callable[[str, str], Optional[str]]] = None,
    parse_robot_file_fn: Optional[Callable[[str], RobotTestStructure]] = None
) -> List[SagaEvent]:
    """
    Build complete SAGA structure with all events mapped upfront - pure function.
    
    Args:
        dag_config: DAG configuration dictionary
        rpa_key_id: RPA key identifier
        robots_base_path: Base path to rpa-robots directory
        occurred_at: Optional timestamp for events (defaults to now)
        find_robot_file_fn: Optional function to find robot file (for testing)
        parse_robot_file_fn: Optional function to parse robot file (for testing)
        
    Returns:
        List of SagaEvent objects in execution order
    """
    if occurred_at is None:
        occurred_at = datetime.utcnow()
    
    if find_robot_file_fn is None:
        find_robot_file_fn = _default_find_robot_file
    if parse_robot_file_fn is None:
        parse_robot_file_fn = parse_robot_file
    
    dag_structure = parse_dag_structure(dag_config)
    execution_order = build_task_execution_order(dag_structure)
    
    events = _build_task_events(
        dag_structure,
        execution_order,
        robots_base_path,
        occurred_at,
        find_robot_file_fn,
        parse_robot_file_fn
    )
    
    saga_complete_event = _create_saga_complete_event(dag_structure.dag_id, occurred_at)
    events.append(saga_complete_event)
    
    logger.info(f"Built complete SAGA structure with {len(events)} events for DAG {dag_structure.dag_id}")
    
    return events


def _build_task_events(
    dag_structure: DAGStructure,
    execution_order: List[str],
    robots_base_path: str,
    occurred_at: datetime,
    find_robot_file_fn: Callable[[str, str], Optional[str]],
    parse_robot_file_fn: Callable[[str], RobotTestStructure]
) -> List[SagaEvent]:
    """Build events for all tasks in execution order - pure function."""
    events: List[SagaEvent] = []
    
    for task_id in execution_order:
        task = dag_structure.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found in DAG structure")
            continue
        
        task_start_event = _create_task_start_event(task_id, task.task_type, dag_structure.dag_id, occurred_at)
        events.append(task_start_event)
        
        if task.task_type == "RobotFrameworkOperator":
            robot_events = _build_robot_events(
                task,
                dag_structure.dag_id,
                robots_base_path,
                occurred_at,
                find_robot_file_fn,
                parse_robot_file_fn
            )
            events.extend(robot_events)
        
        task_complete_event = _create_task_complete_event(task_id, task.task_type, dag_structure.dag_id, occurred_at)
        events.append(task_complete_event)
    
    return events


def _create_task_start_event(
    task_id: str,
    task_type: str,
    dag_id: str,
    occurred_at: datetime
) -> SagaEvent:
    """Create task start event - pure function."""
    return SagaEvent(
        event_type="TaskPending",
        event_data={
            "task_id": task_id,
            "task_type": task_type,
            "status": "PENDING",
            "step": "task_start"
        },
        task_id=task_id,
        dag_id=dag_id,
        occurred_at=occurred_at
    )


def _create_task_complete_event(
    task_id: str,
    task_type: str,
    dag_id: str,
    occurred_at: datetime
) -> SagaEvent:
    """Create task complete event - pure function."""
    return SagaEvent(
        event_type="TaskPending",
        event_data={
            "task_id": task_id,
            "task_type": task_type,
            "status": "PENDING",
            "step": "task_complete"
        },
        task_id=task_id,
        dag_id=dag_id,
        occurred_at=occurred_at
    )


def _create_saga_complete_event(dag_id: str, occurred_at: datetime) -> SagaEvent:
    """Create saga complete event - pure function."""
    return SagaEvent(
        event_type="SagaPending",
        event_data={
            "status": "PENDING",
            "step": "saga_complete"
        },
        task_id=None,
        dag_id=dag_id,
        occurred_at=occurred_at
    )


def _build_robot_events(
    task: DAGTask,
    dag_id: str,
    robots_base_path: str,
    occurred_at: datetime,
    find_robot_file_fn: Callable[[str, str], Optional[str]],
    parse_robot_file_fn: Callable[[str], RobotTestStructure]
) -> List[SagaEvent]:
    """
    Build events for Robot Framework steps - pure function.
    
    Args:
        task: DAGTask of type RobotFrameworkOperator
        dag_id: DAG ID
        robots_base_path: Base path to rpa-robots directory
        occurred_at: Timestamp for events
        find_robot_file_fn: Function to find robot file
        parse_robot_file_fn: Function to parse robot file
        
    Returns:
        List of SagaEvent objects for Robot Framework steps
    """
    robot_file_path = _resolve_robot_file_path(
        task,
        robots_base_path,
        find_robot_file_fn
    )
    
    if not robot_file_path:
        logger.warning(f"Robot Framework file not found for task {task.task_id}")
        return []
    
    try:
        robot_structure = parse_robot_file_fn(robot_file_path)
    except Exception as e:
        logger.error(f"Error parsing Robot Framework file {robot_file_path}: {e}")
        return []
    
    events = _create_robot_step_events(robot_structure, task.task_id, dag_id, occurred_at)
    return events


def _resolve_robot_file_path(
    task: DAGTask,
    robots_base_path: str,
    find_robot_file_fn: Callable[[str, str], Optional[str]]
) -> Optional[str]:
    """Resolve Robot Framework file path - pure function."""
    if task.robot_test_file:
        if os.path.exists(task.robot_test_file):
            return task.robot_test_file
        possible_path = os.path.join(robots_base_path, "tests", task.robot_test_file)
        if os.path.exists(possible_path):
            return possible_path
    
    rpa_key = task.rpa_key_id or ""
    return find_robot_file_fn(rpa_key, robots_base_path)


def _create_robot_step_events(
    robot_structure: RobotTestStructure,
    task_id: str,
    dag_id: str,
    occurred_at: datetime
) -> List[SagaEvent]:
    """Create events for Robot Framework test cases and keywords - pure function."""
    events: List[SagaEvent] = []
    
    for test_case in robot_structure.test_cases:
        event = _create_robot_step_event(
            test_case.step_name,
            test_case.step_type,
            task_id,
            dag_id,
            occurred_at
        )
        events.append(event)
    
    for keyword in robot_structure.keywords:
        event = _create_robot_step_event(
            keyword.step_name,
            keyword.step_type,
            task_id,
            dag_id,
            occurred_at
        )
        events.append(event)
    
    return events


def _create_robot_step_event(
    step_name: str,
    step_type: str,
    task_id: str,
    dag_id: str,
    occurred_at: datetime
) -> SagaEvent:
    """Create Robot Framework step event - pure function."""
    return SagaEvent(
        event_type="RobotStepPending",
        event_data={
            "step_name": step_name,
            "step_type": step_type,
            "status": "PENDING"
        },
        task_id=task_id,
        dag_id=dag_id,
        occurred_at=occurred_at
    )


def _default_find_robot_file(rpa_key: str, base_path: str) -> Optional[str]:
    """Default function to find robot file."""
    return find_robot_file(rpa_key, base_path)

