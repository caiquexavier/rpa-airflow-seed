"""Unit tests for errors module."""
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.validations.errors import (
    create_validation_error_response, create_internal_error_response
)


class TestCreateValidationErrorResponse:
    """Test create_validation_error_response function."""
    
    def test_validation_error_response(self):
        """Test validation error response creation."""
        # Setup
        error = ValidationError.from_exception_data("ValidationError", [
            {
                "type": "missing",
                "loc": ("rpa_key_id",),
                "msg": "Field required",
                "input": {}
            }
        ])
        
        # Execute
        response = create_validation_error_response(error)
        
        # Verify
        assert response.status_code == 400
        response_body = response.body.decode()
        assert "rpa_key_id" in response_body
        assert "Invalid request" in response_body
    
    def test_multiple_validation_errors(self):
        """Test response with multiple validation errors."""
        # Setup - create a simple validation error with multiple issues
        try:
            from src.validations.request_models import RpaRequestModel
            RpaRequestModel(rpa_key_id="", callback_url="not-a-url", rpa_request="not-a-dict")
        except ValidationError as error:
            # Execute
            response = create_validation_error_response(error)
            
            # Verify
            assert response.status_code == 400
            response_body = response.body.decode()
            assert "Invalid request" in response_body
            assert "errors" in response_body


class TestCreateInternalErrorResponse:
    """Test create_internal_error_response function."""
    
    def test_internal_error_response(self):
        """Test internal error response creation."""
        # Execute
        response = create_internal_error_response()
        
        # Verify
        assert response.status_code == 500
        response_body = response.body.decode()
        assert "message" in response_body
        assert "Internal error" in response_body
    
    def test_internal_error_response_structure(self):
        """Test internal error response structure."""
        # Execute
        response = create_internal_error_response()
        
        # Verify
        assert response.status_code == 500
        response_body = response.body.decode()
        assert isinstance(response_body, str)
        assert len(response_body) > 0
