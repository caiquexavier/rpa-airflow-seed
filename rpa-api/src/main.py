"""FastAPI application entrypoint for rpa-api."""
import logging
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Load environment variables from .env file
load_dotenv()

from .controllers.request_controller import handle_request_rpa_exec
from .validations.request_models import RpaRequestModel
from .validations.errors import create_validation_error_response, create_internal_error_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="rpa-api")


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    return create_validation_error_response(exc)


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}")
    return create_internal_error_response()


@app.post("/request_rpa_exec", status_code=202)
async def request_rpa_exec(payload: RpaRequestModel) -> Dict[str, Any]:
    """Request RPA execution by publishing to queue."""
    try:
        return handle_request_rpa_exec(payload)
    except Exception as e:
        logger.error(f"Error in request_rpa_exec: {e}")
        raise HTTPException(status_code=500, detail="Internal error")