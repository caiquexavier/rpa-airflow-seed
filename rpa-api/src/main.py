"""FastAPI application entrypoint for rpa-api."""
import logging
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Load environment variables from .env file
load_dotenv()

from .presentation.dtos.errors import create_validation_error_response, create_internal_error_response
from .presentation.routers.saga_router import router as saga_router
from .presentation.routers.robot_operator_saga_router import router as robot_operator_saga_router
from .presentation.routers.ocr_pdf_router import router as ocr_pdf_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Reduce pika logging to WARNING to reduce noise
logging.getLogger('pika').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(title="rpa-api")

# Include routers
app.include_router(saga_router)
app.include_router(robot_operator_saga_router)
app.include_router(ocr_pdf_router)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.error(f"Pydantic validation error on {request.url.path}: {exc.errors()}")
    return create_validation_error_response(exc)


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}")
    return create_internal_error_response()

