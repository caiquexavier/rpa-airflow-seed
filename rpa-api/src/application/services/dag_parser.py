"""DAG parser service - Extracts task structure from DAG configuration."""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DAGTask:
    """Represents a DAG task."""
    task_id: str
    task_type: str  # Operator type: PythonOperator, RobotFrameworkOperator, StartSagaOperator
    operator_class: Optional[str] = None
    dependencies: List[str] = None  # Upstream task_ids
    robot_test_file: Optional[str] = None  # Robot Framework test file path
    rpa_key_id: Optional[str] = None  # RPA key identifier
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class DAGStructure:
    """Represents complete DAG structure with tasks and dependencies."""
    dag_id: str
    tasks: List[DAGTask]
    task_dependencies: Dict[str, List[str]]  # task_id -> downstream task_ids
    
    def get_task(self, task_id: str) -> Optional[DAGTask]:
        """Get task by task_id."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def get_robot_tasks(self) -> List[DAGTask]:
        """Get all RobotFrameworkOperator tasks."""
        return [task for task in self.tasks if task.task_type == "RobotFrameworkOperator"]


def parse_dag_structure(dag_config: Dict[str, Any]) -> DAGStructure:
    """
    Parse DAG structure from configuration - pure function.
    
    Args:
        dag_config: Dictionary with dag_id and tasks list
        
    Returns:
        DAGStructure with parsed tasks and dependency map
    """
    dag_id = dag_config.get("dag_id", "")
    tasks_config = dag_config.get("tasks", [])
    
    tasks = _build_tasks_from_config(tasks_config)
    task_dependencies = _build_dependency_map(tasks)
    
    return DAGStructure(
        dag_id=dag_id,
        tasks=tasks,
        task_dependencies=task_dependencies
    )


def _build_tasks_from_config(tasks_config: List[Dict[str, Any]]) -> List[DAGTask]:
    """Build DAGTask list from configuration - pure function."""
    tasks = []
    for task_config in tasks_config:
        task = DAGTask(
            task_id=task_config.get("task_id", ""),
            task_type=task_config.get("task_type", "Unknown"),
            operator_class=task_config.get("operator_class"),
            dependencies=task_config.get("dependencies", []),
            robot_test_file=task_config.get("robot_test_file"),
            rpa_key_id=task_config.get("rpa_key_id")
        )
        tasks.append(task)
    return tasks


def _build_dependency_map(tasks: List[DAGTask]) -> Dict[str, List[str]]:
    """Build reverse dependency map (upstream -> downstream) - pure function."""
    task_dependencies: Dict[str, List[str]] = {task.task_id: [] for task in tasks}
    
    for task in tasks:
        for dep in task.dependencies:
            if dep in task_dependencies:
                task_dependencies[dep].append(task.task_id)
    
    return task_dependencies


def build_task_execution_order(dag_structure: DAGStructure) -> List[str]:
    """
    Build task execution order using topological sort - pure function.
    
    Args:
        dag_structure: DAGStructure with tasks and dependencies
        
    Returns:
        List of task_ids in execution order
    """
    in_degree = _calculate_in_degree(dag_structure)
    return _topological_sort(dag_structure, in_degree)


def _calculate_in_degree(dag_structure: DAGStructure) -> Dict[str, int]:
    """Calculate incoming dependency count for each task - pure function."""
    in_degree: Dict[str, int] = {task.task_id: 0 for task in dag_structure.tasks}
    
    for task in dag_structure.tasks:
        for dep in task.dependencies:
            if dep in in_degree:
                in_degree[task.task_id] += 1
    
    return in_degree


def _topological_sort(
    dag_structure: DAGStructure,
    in_degree: Dict[str, int]
) -> List[str]:
    """Perform topological sort to determine execution order - pure function."""
    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    execution_order = []
    
    while queue:
        task_id = queue.pop(0)
        execution_order.append(task_id)
        
        # Reduce in-degree for dependent tasks
        for dependent_task_id in dag_structure.task_dependencies.get(task_id, []):
            in_degree[dependent_task_id] -= 1
            if in_degree[dependent_task_id] == 0:
                queue.append(dependent_task_id)
    
    return execution_order

