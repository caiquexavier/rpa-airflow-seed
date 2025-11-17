"""Extended unit tests for webhook service."""
import pytest
from unittest.mock import Mock, patch
import os

from src.services.webhook import call_webhook


@pytest.mark.unit
class TestCallWebhookExtended:
    """Extended tests for call_webhook function."""

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_success_with_error_in_response(self, mock_post):
        """Test webhook call when rpa_response contains error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="FAIL",
            rpa_response={"error": "Error from response"},
            error_message="Error from response",
            saga=None
        )

        assert result is True
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload["status"] == "FAIL"
        assert payload["error_message"] == "Error from response"

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_fallback_to_docker_service(self, mock_post):
        """Test webhook call with fallback to Docker service name."""
        import requests
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            Mock(status_code=200)  # Success on second try
        ]

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={},
            error_message=None,
            saga=None
        )

        assert result is True
        # Should have tried both URLs
        assert mock_post.call_count == 2

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://rpa-api:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_fallback_to_localhost(self, mock_post):
        """Test webhook call with fallback from Docker service to localhost."""
        import requests
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            Mock(status_code=200)  # Success on second try
        ]

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={},
            error_message=None,
            saga=None
        )

        assert result is True
        assert mock_post.call_count == 2

    @patch.dict(os.environ, {'RPA_API_WEBHOOK_URL': 'http://localhost:3000/updateRpaExecution'})
    @patch('src.services.webhook.requests.post')
    def test_call_webhook_all_urls_fail(self, mock_post):
        """Test webhook call when all URLs fail."""
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
    def test_call_webhook_generic_exception(self, mock_post):
        """Test webhook call with generic exception."""
        mock_post.side_effect = Exception("Unexpected error")

        result = call_webhook(
            exec_id=1,
            rpa_key_id="test_rpa",
            status="SUCCESS",
            rpa_response={},
            error_message=None,
            saga=None
        )

        assert result is False

