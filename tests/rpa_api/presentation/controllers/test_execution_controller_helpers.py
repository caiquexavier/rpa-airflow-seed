"""Unit tests for execution controller helper functions."""
import pytest
from unittest.mock import Mock

from src.presentation.controllers.execution_controller import _payload_to_dict


@pytest.mark.unit
class TestPayloadToDict:
    """Tests for _payload_to_dict helper function."""

    def test_payload_to_dict_with_dict(self):
        """Test with dict payload."""
        payload = {"key": "value"}
        result = _payload_to_dict(payload)
        assert result == payload
        assert result is payload  # Should return same object

    def test_payload_to_dict_with_pydantic_v2(self):
        """Test with Pydantic v2 model."""
        class MockPydanticV2:
            def model_dump(self):
                return {"key": "value"}
        
        payload = MockPydanticV2()
        result = _payload_to_dict(payload)
        assert result == {"key": "value"}

    def test_payload_to_dict_with_pydantic_v1(self):
        """Test with Pydantic v1 model."""
        class MockPydanticV1:
            def dict(self):
                return {"key": "value"}
        
        payload = MockPydanticV1()
        result = _payload_to_dict(payload)
        assert result == {"key": "value"}

    def test_payload_to_dict_fallback(self):
        """Test fallback for other types."""
        payload = "string"
        result = _payload_to_dict(payload)
        assert result == "string"

