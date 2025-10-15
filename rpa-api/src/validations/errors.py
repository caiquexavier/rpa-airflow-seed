"""Error handling utilities for validation errors."""
from typing import List, Dict, Any
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def create_validation_error_response(validation_error: ValidationError) -> JSONResponse:
    """Convert Pydantic validation error to standardized error response."""
    errors = []
    
    for error in validation_error.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        error_type = error["type"]
        error_msg = error["msg"]
        
        # Map specific error types to user-friendly messages
        if field == "rpa_key_id" and error_type == "missing":
            error_msg = "rpa_key_id is required and must be a non-empty string"
        elif field == "rpa_key_id" and error_type == "string_too_short":
            error_msg = "rpa_key_id is required and must be a non-empty string"
        elif field == "callback_url" and error_type in ["url_parsing", "url_scheme"]:
            error_msg = "Invalid URL"
        elif field == "rpa_request" and error_type == "dict_type":
            error_msg = "rpa_request must be a JSON object"
        elif error_type == "extra_forbidden":
            error_msg = f"unexpected field '{error['input']}'"
        
        errors.append({
            "field": field,
            "error": error_msg
        })
    
    return JSONResponse(
        status_code=400,
        content={
            "message": "Invalid request",
            "errors": errors
        }
    )


def create_internal_error_response() -> JSONResponse:
    """Create standardized internal error response."""
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal error",
            "errors": []
        }
    )
