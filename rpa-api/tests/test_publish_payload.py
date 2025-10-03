"""Unit tests for publish payload validation."""
import pytest
from pydantic import ValidationError

from src.validations.publish_payload import PublishPayload


class TestPublishPayload:
    """Test cases for PublishPayload validation."""
    
    def test_valid_payload_with_rpa_id(self):
        """Test valid payload with rpa-id field."""
        payload = {"rpa-id": "job-001", "other_field": "value"}
        model = PublishPayload(**payload)
        
        assert model.rpa_id == "job-001"
        assert model.to_dict() == {"rpa-id": "job-001", "other_field": "value"}
    
    def test_valid_payload_with_extra_fields(self):
        """Test payload with extra fields is allowed."""
        payload = {
            "rpa-id": "test-123",
            "nested": {"data": True},
            "array": [1, 2, 3]
        }
        model = PublishPayload(**payload)
        
        assert model.rpa_id == "test-123"
        assert model.to_dict() == payload
    
    def test_missing_rpa_id_raises_error(self):
        """Test that missing rpa-id raises ValidationError."""
        payload = {"other_field": "value"}
        
        with pytest.raises(ValidationError) as exc_info:
            PublishPayload(**payload)
        
        assert "rpa-id" in str(exc_info.value)
    
    def test_empty_rpa_id_raises_error(self):
        """Test that empty rpa-id raises ValidationError."""
        payload = {"rpa-id": ""}
        
        with pytest.raises(ValidationError) as exc_info:
            PublishPayload(**payload)
        
        assert "rpa-id" in str(exc_info.value)
    
    def test_non_string_rpa_id_raises_error(self):
        """Test that non-string rpa-id raises ValidationError."""
        payload = {"rpa-id": 123}
        
        with pytest.raises(ValidationError) as exc_info:
            PublishPayload(**payload)
        
        assert "rpa-id" in str(exc_info.value)
    
    def test_to_dict_preserves_alias(self):
        """Test that to_dict preserves the hyphenated field name."""
        payload = {"rpa-id": "test-456"}
        model = PublishPayload(**payload)
        result = model.to_dict()
        
        assert "rpa-id" in result
        assert "rpa_id" not in result
        assert result["rpa-id"] == "test-456"
