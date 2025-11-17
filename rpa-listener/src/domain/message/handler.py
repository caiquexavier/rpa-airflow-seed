"""Message handler for RobotOperatorSaga messages."""
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

from ..robot.executor import execute_robot_tests
from ..robot.response_builder import build_rpa_response
from ..robot.step_results import extract_top_level_step_results, StepResult
from ..saga.manager import (
    create_robot_event,
    add_event_to_saga,
    log_saga
)
from ...infrastructure.http.api_client import update_robot_operator_saga
from ...infrastructure.http.webhook_client import call_callback_webhook

logger = logging.getLogger(__name__)


def handle_message(
    message: Dict,
    project_path: Path,
    robot_exe: Path,
    tests_path: Path,
    results_dir: Path
) -> bool:
    """Handle RobotOperatorSaga message."""
    robot_operator_saga_id = message.get('robot_operator_saga_id')
    if not robot_operator_saga_id:
        raise ValueError("Missing required field: robot_operator_saga_id")
    
    saga_id = message.get('saga_id')
    robot_operator_id = message.get('robot_operator_id')
    robot_test_file = message.get('robot_test_file')
    callback_path = message.get('callback_path')
    robot_saga = message.get('robot_saga', {})
    
    logger.info(
        "Handling RobotOperatorSaga message",
        extra={
            "robot_operator_saga_id": robot_operator_saga_id,
            "robot_operator_id": robot_operator_id,
            "saga_id": saga_id,
            "callback_path": callback_path,
        },
    )
    
    log_saga(robot_saga)
    
    robot_test_path = _determine_test_file_path(tests_path, robot_test_file, robot_operator_id)
    logger.debug("Resolved robot test path: %s", robot_test_path)
    
    success, execution_error = execute_robot_tests(
        project_path, robot_exe, robot_test_path, results_dir, message
    )
    logger.info(
        "Robot execution finished",
        extra={"success": success, "execution_error": execution_error},
    )
    
    try:
        rpa_response = build_rpa_response(message, results_dir, success)
    except Exception as e:
        rpa_response = {"error": str(e)} if not success else {}
    
    if not success:
        error_message = execution_error or rpa_response.get("error") or "Robot execution failed"
        status = "FAIL"
    else:
        error_message = None
        status = "SUCCESS"
    
    robot_saga.setdefault("robot_operator_id", robot_operator_id)
    step_results = extract_top_level_step_results(results_dir)
    
    if robot_operator_saga_id and step_results:
        robot_saga = _publish_step_events(
            robot_operator_saga_id,
            robot_operator_id,
            step_results,
            robot_saga
        )
    
    try:
        robot_event = create_robot_event(
            robot_operator_id, success, status, rpa_response, error_message
        )
        new_state = "COMPLETED" if success else "FAILED"
        robot_saga = add_event_to_saga(robot_saga, robot_event, new_state)
        log_saga(robot_saga)
    except Exception as saga_error:
        logger.exception("Failed to append robot event to saga: %s", saga_error)
    
    if robot_operator_saga_id:
        final_event_type = "RobotOperatorSagaCompleted" if success else "RobotOperatorSagaFailed"
        try:
            saga_updated = update_robot_operator_saga(
                robot_operator_saga_id,
                status,
                rpa_response,
                error_message,
                robot_saga,
                event_type_override=final_event_type,
                step_id_override=None,
            )
            logger.info(
                "RobotOperatorSaga updated",
                extra={
                    "robot_operator_saga_id": robot_operator_saga_id,
                    "status": status,
                    "update_success": saga_updated,
                },
            )
        except Exception:
            logger.exception(
                "Unexpected error while calling RPA API for saga %s", robot_operator_saga_id
            )
        
        if callback_path:
            try:
                webhook_ok = call_callback_webhook(callback_path, saga_id, robot_saga, status)
                logger.info(
                    "Callback webhook dispatched",
                    extra={
                        "callback_path": callback_path,
                        "status": status,
                        "webhook_success": webhook_ok,
                    },
                )
            except Exception:
                logger.exception(
                    "Unexpected error while calling callback webhook for saga %s", robot_operator_saga_id
                )
    
    return success


def _determine_test_file_path(tests_path: Path, robot_test_file: Optional[str], robot_operator_id: Optional[str]) -> Path:
    """Determine robot test file path from message."""
    if robot_test_file:
        return tests_path / robot_test_file
    elif robot_operator_id:
        return tests_path / f"{robot_operator_id}.robot"
    else:
        raise ValueError("Cannot determine test file: missing both robot_test_file and robot_operator_id")


def _publish_step_events(
    robot_operator_saga_id: int,
    robot_operator_id: Optional[str],
    step_results: list[StepResult],
    robot_saga: Dict
) -> Dict:
    """Record each top-level Robot step as a saga event."""
    for step in step_results:
        event_type = _map_status_to_event_type(step.status)
        event_data = {
            "step_name": step.name,
            "status": step.status,
            "order": step.order,
            "error_message": step.message,
            "test_case": step.test_name,
            "started_at": step.started_at,
            "elapsed": step.elapsed,
        }
        step_id = f"{robot_operator_id}:{step.order:02d}" if robot_operator_id else f"step-{step.order:02d}"
        try:
            update_robot_operator_saga(
                robot_operator_saga_id,
                status=step.status,
                rpa_response={},
                error_message=step.message,
                robot_saga=robot_saga,
                event_type_override=event_type,
                event_data_override=event_data,
                step_id_override=step_id,
            )
        except Exception:
            logger.exception(
                "Failed to record saga step event",
                extra={
                    "robot_operator_saga_id": robot_operator_saga_id,
                    "step_name": step.name,
                    "order": step.order,
                    "status": step.status,
                },
            )
            continue
        
        # Mirror the step in the in-memory saga representation so callbacks can see it
        robot_saga = add_event_to_saga(
            robot_saga,
            {
                "event_type": event_type,
                "event_data": event_data,
                "step_id": step_id,
                "robot_operator_id": robot_operator_id,
            },
            robot_saga.get("current_state", "RUNNING")
        )
    return robot_saga


def _map_status_to_event_type(status: str) -> str:
    normalized = (status or "").upper()
    if normalized == "PASS" or normalized == "SUCCESS":
        return "RobotOperatorStepCompleted"
    if normalized == "FAIL":
        return "RobotOperatorStepFailed"
    if normalized in {"NOT RUN", "SKIP", "SKIPPED"}:
        return "RobotOperatorStepSkipped"
    return "RobotOperatorStepStatus"

