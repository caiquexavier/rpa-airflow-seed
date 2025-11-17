"""Saga router - Endpoints for saga operations."""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from ..controllers.saga_controller import (
    handle_create_saga,
    handle_update_saga_event,
    # handle_request_robot_execution  # TODO: Re-enable after refactoring finishes
)
from ..dtos.saga_models import (
    CreateSagaRequest,
    UpdateSagaEventRequest,
    # RequestRobotExecutionRequest  # TODO: Re-enable after refactoring finishes
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/saga", tags=["Saga"])


@router.post("/create", status_code=201)
async def create_saga(payload: CreateSagaRequest) -> Dict[str, Any]:
    """
    Create a new Saga.
    
    Used by Airflow DAGs to create saga orchestrations.
    """
    try:
        result = handle_create_saga(payload)
        return result
    except ValueError as e:
        logger.warning(f"Validation error in create_saga: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in create_saga: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.post("/event", status_code=200)
async def update_saga_event(payload: UpdateSagaEventRequest) -> Dict[str, Any]:
    """
    Update Saga with a new event.
    
    Used by Airflow DAGs to record task events.
    """
    try:
        result = handle_update_saga_event(payload)
        return result
    except ValueError as e:
        logger.warning(f"Validation error in update_saga_event: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in update_saga_event: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


# TODO: Re-enable after refactoring finishes - Robot execution endpoint needs to be fully implemented
# @router.post("/request_robot_execution", status_code=202)
# async def request_robot_execution(payload: RequestRobotExecutionRequest) -> Dict[str, Any]:
#     """
#     Request robot execution for a saga.
#     
#     Publishes saga to RabbitMQ queue for robot execution.
#     Used by Airflow RobotFrameworkOperator.
#     """
#     try:
#         result = handle_request_robot_execution(payload)
#         return result
#     except ValueError as e:
#         logger.warning(f"Validation error in request_robot_execution: {e}")
#         raise HTTPException(status_code=422, detail=str(e))
#     except Exception as e:
#         logger.error(f"Error in request_robot_execution: {e}")
#         raise HTTPException(status_code=500, detail="Internal error")

