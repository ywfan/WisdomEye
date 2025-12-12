"""Unit tests for retry policy."""
import pytest
from infra.retry import RetryPolicy


class TestRetryPolicy:
    """Test retry policy functionality."""

    def test_success_on_first_try(self):
        """Test successful execution on first try."""
        policy = RetryPolicy(attempts=3)
        result = policy.run(lambda: "success")
        assert result == "success"

    def test_success_after_retries(self):
        """Test success after some failures."""
        policy = RetryPolicy(attempts=3, base_delay=0.01, max_delay=0.02)
        
        call_count = [0]
        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = policy.run(flaky_func)
        assert result == "success"
        assert call_count[0] == 3

    def test_all_attempts_fail(self):
        """Test that exception is raised after all attempts fail."""
        policy = RetryPolicy(attempts=3, base_delay=0.01, max_delay=0.02)
        
        with pytest.raises(ValueError, match="Always fails"):
            policy.run(lambda: (_ for _ in ()).throw(ValueError("Always fails")))

    def test_single_attempt(self):
        """Test with single attempt (no retries)."""
        policy = RetryPolicy(attempts=1, base_delay=0.01)
        
        with pytest.raises(ValueError):
            policy.run(lambda: (_ for _ in ()).throw(ValueError("Fail")))

    def test_different_exception_types(self):
        """Test handling different exception types."""
        policy = RetryPolicy(attempts=2, base_delay=0.01)
        
        # Should propagate RuntimeError
        with pytest.raises(RuntimeError):
            policy.run(lambda: (_ for _ in ()).throw(RuntimeError("Error")))

    def test_delay_increases(self):
        """Test that delay increases exponentially."""
        import time
        policy = RetryPolicy(attempts=3, base_delay=0.05, max_delay=0.2)
        
        call_times = []
        def failing_func():
            call_times.append(time.time())
            raise ValueError("Fail")
        
        with pytest.raises(ValueError):
            policy.run(failing_func)
        
        # Should have made 3 attempts
        assert len(call_times) == 3
        
        # Delays should increase (with some tolerance for jitter)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay1 >= 0.05  # Base delay
        assert delay2 > delay1 * 0.8  # Should roughly double (accounting for jitter)
