"""Unit tests for error handling."""
import pytest
from infra.errors import ExternalError, classify_http


class TestExternalError:
    """Test ExternalError exception."""

    def test_error_with_code_only(self):
        """Test error with code only."""
        error = ExternalError("rate_limited")
        assert error.code == "rate_limited"
        assert error.detail == ""
        assert "rate_limited:" in str(error)

    def test_error_with_code_and_detail(self):
        """Test error with code and detail."""
        error = ExternalError("server_error", "Connection timeout")
        assert error.code == "server_error"
        assert error.detail == "Connection timeout"
        assert "server_error:Connection timeout" in str(error)

    def test_error_is_exception(self):
        """Test that ExternalError is an Exception."""
        error = ExternalError("test")
        assert isinstance(error, Exception)

    def test_error_can_be_raised(self):
        """Test that error can be raised and caught."""
        with pytest.raises(ExternalError) as exc_info:
            raise ExternalError("test_code", "test detail")
        
        assert exc_info.value.code == "test_code"
        assert exc_info.value.detail == "test detail"


class TestClassifyHTTP:
    """Test HTTP status classification."""

    def test_success_codes(self):
        """Test successful status codes."""
        assert classify_http(200) == "ok"
        assert classify_http(201) == "ok"
        assert classify_http(204) == "ok"
        assert classify_http(299) == "ok"

    def test_client_errors(self):
        """Test 4xx client errors."""
        assert classify_http(400) == "bad_request"
        assert classify_http(404) == "bad_request"
        assert classify_http(422) == "bad_request"

    def test_auth_errors(self):
        """Test authentication/authorization errors."""
        assert classify_http(401) == "unauthorized"
        assert classify_http(403) == "unauthorized"

    def test_rate_limit(self):
        """Test rate limit status."""
        assert classify_http(429) == "rate_limited"

    def test_server_errors(self):
        """Test 5xx server errors."""
        assert classify_http(500) == "server_error"
        assert classify_http(502) == "server_error"
        assert classify_http(503) == "server_error"
        assert classify_http(599) == "server_error"

    def test_informational_codes(self):
        """Test 1xx informational codes."""
        # These should be treated as OK since they're not errors
        assert classify_http(100) == "ok"
        assert classify_http(101) == "ok"

    def test_redirection_codes(self):
        """Test 3xx redirection codes."""
        # These should be treated as OK since they're not errors
        assert classify_http(301) == "ok"
        assert classify_http(302) == "ok"
        assert classify_http(304) == "ok"
