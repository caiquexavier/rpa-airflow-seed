"""RobotOperatorSaga router - Endpoints for robot operator saga operations."""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from ..controllers.robot_operator_saga_controller import (
    handle_create_robot_operator_saga,
    handle_update_robot_operator_saga_event
)
from ..dtos.robot_operator_saga_models import (
    CreateRobotOperatorSagaRequest,
    UpdateRobotOperatorSagaEventRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/robot-operator-saga", tags=["RobotOperatorSaga"])


@router.post("/start", status_code=201)
async def start_robot_operator_saga(payload: CreateRobotOperatorSagaRequest) -> Dict[str, Any]:
    """
    Start a new RobotOperatorSaga.
    
    Used to create robot operator saga orchestrations.
    """
    try:
        result = handle_create_robot_operator_saga(payload)
        return result
    except ValueError as e:
        logger.warning(f"Validation error in start_robot_operator_saga: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in start_robot_operator_saga: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.post("/{robot_operator_saga_id}/events/step", status_code=200)
async def update_robot_operator_saga_step(
    robot_operator_saga_id: int,
    payload: UpdateRobotOperatorSagaEventRequest
) -> Dict[str, Any]:
    """
    Update RobotOperatorSaga with a new step event.
    
    Used to record robot operator step events.
    """
    try:
        # Ensure the saga_id in payload matches the path parameter
        if payload.robot_operator_saga_id != robot_operator_saga_id:
            raise ValueError(f"Saga ID mismatch: path={robot_operator_saga_id}, payload={payload.robot_operator_saga_id}")
        result = handle_update_robot_operator_saga_event(payload)
        return result
    except ValueError as e:
        logger.warning(f"Validation error in update_robot_operator_saga_step: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in update_robot_operator_saga_step: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

