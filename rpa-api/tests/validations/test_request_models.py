"""Unit tests for request_models module."""
import pytest
from pydantic import ValidationError

from src.validations.request_models import RpaRequestModel


class TestRpaRequestModel:
    """Test RpaRequestModel validation."""
    
    def test_valid_request_with_all_fields(self):
        """Test valid request with all fields."""
        request = RpaRequestModel(
            rpa_key_id="job-001",
            callback_url="http://localhost:3000/callback",
            rpa_request={"nota_fiscal": "12345"}
        )
        
        assert request.rpa_key_id == "job-001"
        assert str(request.callback_url) == "http://localhost:3000/callback"
        assert request.rpa_request == {"nota_fiscal": "12345"}
    
    def test_valid_request_minimal(self):
        """Test valid request with only required fields."""
        request = RpaRequestModel(rpa_key_id="job-001")
        
        assert request.rpa_key_id == "job-001"
        assert request.callback_url is None
        assert request.rpa_request is None
    
    def test_empty_rpa_key_id_rejected(self):
        """Test that empty rpa_key_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RpaRequestModel(rpa_key_id="")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "string_too_short"
        assert "rpa_key_id" in str(errors[0]["loc"])
    
    def test_whitespace_only_rpa_key_id_rejected(self):
        """Test that whitespace-only rpa_key_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RpaRequestModel(rpa_key_id="   ")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "string_too_short"
    
    def test_invalid_callback_url_rejected(self):
        """Test that invalid callback URL is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RpaRequestModel(
                rpa_key_id="job-001",
                callback_url="not-a-url"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "url_parsing"
        assert "callback_url" in str(errors[0]["loc"])
    
    def test_valid_callback_url_accepted(self):
        """Test that valid callback URL is accepted."""
        request = RpaRequestModel(
            rpa_key_id="job-001",
            callback_url="https://api.example.com/webhook"
        )
        
        assert str(request.callback_url) == "https://api.example.com/webhook"
    
    def test_rpa_request_must_be_dict(self):
        """Test that rpa_request must be a dictionary."""
        with pytest.raises(ValidationError) as exc_info:
            RpaRequestModel(
                rpa_key_id="job-001",
                rpa_request=["not", "a", "dict"]
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "dict_type"
        assert "rpa_request" in str(errors[0]["loc"])
    
    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RpaRequestModel(
                rpa_key_id="job-001",
                extra_field="not allowed"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert "extra_field" in str(errors[0]["loc"])
    
    def test_rpa_key_id_strips_whitespace(self):
        """Test that rpa_key_id strips whitespace."""
        request = RpaRequestModel(rpa_key_id="  job-001  ")
        
        assert request.rpa_key_id == "job-001"
    
    def test_none_values_handled_correctly(self):
        """Test that None values are handled correctly."""
        request = RpaRequestModel(
            rpa_key_id="job-001",
            callback_url=None,
            rpa_request=None
        )
        
        assert request.rpa_key_id == "job-001"
        assert request.callback_url is None
        assert request.rpa_request is None
