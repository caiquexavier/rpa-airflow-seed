"""Unit tests for error DTOs."""
import pytest
from unittest.mock import Mock
from pydantic import ValidationError

from src.presentation.dtos.errors import (
    create_validation_error_response, create_internal_error_response
)


@pytest.mark.unit
class TestCreateValidationErrorResponse:
    """Tests for create_validation_error_response function."""

    def test_create_validation_error_response_basic(self):
        """Test creating validation error response."""
        error = ValidationError.from_exception_data(
            "TestModel",
            [{"type": "missing", "loc": ("field",), "msg": "Field required"}]
        )

        response = create_validation_error_response(error)

        assert response.status_code == 422
        content = response.body.decode()
        assert "Validation error" in content
        assert "field" in content

    def test_create_validation_error_response_rpa_key_id_missing(self):
        """Test validation error for missing rpa_key_id."""
        error = ValidationError.from_exception_data(
            "TestModel",
            [{"type": "missing", "loc": ("rpa_key_id",), "msg": "Field required"}]
        )

        response = create_validation_error_response(error)

        assert response.status_code == 422
        content = response.body.decode()
        assert "rpa_key_id is required" in content

    def test_create_validation_error_response_rpa_key_id_too_short(self):
        """Test validation error for rpa_key_id too short."""
        error = ValidationError.from_exception_data(
            "TestModel",
            [{"type": "string_too_short", "loc": ("rpa_key_id",), "msg": "String too short"}]
        )

        response = create_validation_error_response(error)

        assert response.status_code == 422
        content = response.body.decode()
        assert "rpa_key_id is required" in content

    def test_create_validation_error_response_invalid_url(self):
        """Test validation error for invalid URL."""
        error = ValidationError.from_exception_data(
            "TestModel",
            [{"type": "url_parsing", "loc": ("callback_url",), "msg": "Invalid URL"}]
        )

        response = create_validation_error_response(error)

        assert response.status_code == 422
        content = response.body.decode()
        assert "Invalid URL" in content

    def test_create_validation_error_response_extra_forbidden(self):
        """Test validation error for extra forbidden field."""
        error = ValidationError.from_exception_data(
            "TestModel",
            [{"type": "extra_forbidden", "loc": ("extra_field",), "msg": "Extra field", "input": "extra_value"}]
        )

        response = create_validation_error_response(error)

        assert response.status_code == 422
        content = response.body.decode()
        assert "unexpected field" in content

    def test_create_validation_error_response_cleans_ctx(self):
        """Test that validation error response cleans ctx references."""
        error = ValidationError.from_exception_data(
            "TestModel",
            [{"type": "value_error", "loc": ("field",), "msg": "Error message, ctx={'key': 'value'}"}]
        )

        response = create_validation_error_response(error)

        content = response.body.decode()
        assert "ctx" not in content


@pytest.mark.unit
class TestCreateInternalErrorResponse:
    """Tests for create_internal_error_response function."""

    def test_create_internal_error_response(self):
        """Test creating internal error response."""
        response = create_internal_error_response()

        assert response.status_code == 500
        content = response.body.decode()
        assert "Internal error" in content

