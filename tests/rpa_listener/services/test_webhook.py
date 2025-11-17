"""Unit tests for webhook service."""
import pytest
from unittest.mock import Mock, patch
import os

from src.services.webhook import call_webhook


@pytest.mark.unit
class TestCallWebhook:
    """Tests for call_webhook function."""

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_success(self, mock_post):
        """Test successful webhook call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={"result": "ok"},
            error_message=None,
            saga=None
        )

        assert result is True
        mock_post.assert_called_once()

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_fail_status(self, mock_post):
        """Test webhook call with FAIL status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="FAIL",
            rpa_response={"error": "Test error"},
            error_message="Test error",
            saga=None
        )

        assert result is True
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload["status"] == "FAIL"
        assert payload["error_message"] == "Test error"

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_with_saga(self, mock_post):
        """Test webhook call with saga data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        saga = {
            "saga_id": 1,
            "current_state": "COMPLETED",
            "events": []
        }

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={},
            error_message=None,
            saga=saga
        )

        assert result is True
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert "saga" in payload
        assert payload["saga"] == saga

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_connection_error(self, mock_post):
        """Test webhook call with connection error."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={},
            error_message=None,
            saga=None
        )

        assert result is False

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_timeout(self, mock_post):
        """Test webhook call with timeout."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={},
            error_message=None,
            saga=None
        )

        assert result is False

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_non_200_status(self, mock_post):
        """Test webhook call with non-200 status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={},
            error_message=None,
            saga=None
        )

        assert result is False

