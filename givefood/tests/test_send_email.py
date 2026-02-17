import pytest
from unittest.mock import patch, MagicMock
from givefood.func import send_email


class TestSendEmail:
    """Test send_email checks the API response."""

    @patch('givefood.func.requests.post')
    @patch('givefood.func.get_cred')
    def test_send_email_returns_true_on_success(self, mock_get_cred, mock_post):
        mock_get_cred.return_value = "test-token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = send_email(
            to="test@example.com",
            subject="Test",
            body="Test body",
        )

        assert result is True

    @patch('givefood.func.requests.post')
    @patch('givefood.func.get_cred')
    def test_send_email_returns_false_on_error(self, mock_get_cred, mock_post):
        mock_get_cred.return_value = "test-token"
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Invalid email"
        mock_post.return_value = mock_response

        result = send_email(
            to="bad-address",
            subject="Test",
            body="Test body",
        )

        assert result is False

    @patch('givefood.func.logging')
    @patch('givefood.func.requests.post')
    @patch('givefood.func.get_cred')
    def test_send_email_logs_on_failure(self, mock_get_cred, mock_post, mock_logging):
        mock_get_cred.return_value = "test-token"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        send_email(
            to="test@example.com",
            subject="Test",
            body="Test body",
        )

        mock_logging.error.assert_called_once()
        call_args = mock_logging.error.call_args[0][0]
        assert "500" in call_args
        assert "test@example.com" in call_args
