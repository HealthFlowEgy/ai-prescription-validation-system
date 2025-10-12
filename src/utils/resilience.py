"""
Circuit Breakers and Resilience Patterns
Implements fault tolerance for external service calls

Patterns Implemented:
- Circuit Breaker
- Retry with Exponential Backoff
- Timeout
- Bulkhead
- Rate Limiting
"""

import logging
import threading
import time
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict


logger = logging.getLogger(__name__)


# ============================================
# Circuit Breaker State Machine
# ============================================


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping calls to failing services.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Too many failures, calls fail immediately
    - HALF_OPEN: Testing recovery, limited calls allowed

    Usage:
        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            expected_exception=RequestException
        )

        @circuit_breaker
        def call_external_api():
            response = requests.get('https://api.example.com')
            return response.json()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "default",
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit
            name: Circuit breaker name for monitoring
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.Lock()

        # Metrics
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.rejected_calls = 0

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        """
        with self.lock:
            self.total_calls += 1

            # Check if circuit should transition to HALF_OPEN
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(
                        f"Circuit breaker '{self.name}' transitioning to HALF_OPEN"
                    )
                    self.state = CircuitState.HALF_OPEN
                else:
                    # Circuit is open, reject call immediately
                    self.rejected_calls += 1
                    logger.warning(
                        f"Circuit breaker '{self.name}' is OPEN, call rejected",
                        extra={
                            "circuit_breaker": self.name,
                            "state": self.state.value,
                            "failure_count": self.failure_count,
                        },
                    )
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is OPEN"
                    )

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            self.successful_calls += 1
            self.failure_count = 0

            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit breaker '{self.name}' recovered, closing circuit")
                self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failed_calls += 1
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker '{self.name}' threshold reached, opening circuit",
                    extra={
                        "circuit_breaker": self.name,
                        "failure_count": self.failure_count,
                        "threshold": self.failure_threshold,
                    },
                )
                self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return True

        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.recovery_timeout

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "failure_count": self.failure_count,
            "success_rate": (
                self.successful_calls / self.total_calls * 100
                if self.total_calls > 0
                else 0
            ),
        }

    def reset(self):
        """Manually reset circuit breaker."""
        with self.lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open."""



# ============================================
# Retry with Exponential Backoff
# ============================================


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Retry decorator with exponential backoff.

    Usage:
        @retry(max_attempts=3, initial_delay=1.0, exceptions=(RequestException,))
        def call_api():
            response = requests.get('https://api.example.com')
            return response.json()

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)

                    # Log successful retry
                    if attempt > 0:
                        logger.info(
                            f"Function '{func.__name__}' succeeded after {attempt + 1} attempts"
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        # Calculate next delay with exponential backoff
                        current_delay = min(delay, max_delay)

                        logger.warning(
                            f"Function '{func.__name__}' failed (attempt {attempt + 1}/{max_attempts}), "
                            f"retrying in {current_delay}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "delay": current_delay,
                                "error": str(e),
                            },
                        )

                        time.sleep(current_delay)
                        delay *= exponential_base
                    else:
                        logger.error(
                            f"Function '{func.__name__}' failed after {max_attempts} attempts",
                            extra={
                                "function": func.__name__,
                                "attempts": max_attempts,
                                "error": str(e),
                            },
                            exc_info=True,
                        )

            # All retries exhausted
            raise last_exception

        return wrapper

    return decorator


# ============================================
# Timeout Decorator
# ============================================

import signal


class TimeoutException(Exception):
    """Raised when function execution times out."""



def timeout(seconds: int):
    """
    Timeout decorator for functions.

    Usage:
        @timeout(30)
        def slow_function():
            time.sleep(60)  # Will timeout after 30 seconds

    Note: Only works on Unix-based systems (Linux, macOS)
    """

    def decorator(func: Callable) -> Callable:
        def _handle_timeout(signum, frame):
            raise TimeoutException(
                f"Function '{func.__name__}' timed out after {seconds}s"
            )

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set alarm signal
            old_handler = signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Restore old handler and cancel alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

            return result

        return wrapper

    return decorator


# ============================================
# Bulkhead Pattern
# ============================================


class Bulkhead:
    """
    Bulkhead pattern implementation.

    Limits concurrent executions to prevent resource exhaustion.
    Uses semaphore to limit concurrent calls.

    Usage:
        bulkhead = Bulkhead(max_concurrent=10, name="external_api")

        @bulkhead
        def call_external_api():
            response = requests.get('https://api.example.com')
            return response.json()
    """

    def __init__(self, max_concurrent: int = 10, name: str = "default"):
        """
        Initialize bulkhead.

        Args:
            max_concurrent: Maximum concurrent executions
            name: Bulkhead name for monitoring
        """
        self.max_concurrent = max_concurrent
        self.name = name
        self.semaphore = threading.Semaphore(max_concurrent)

        # Metrics
        self.total_calls = 0
        self.active_calls = 0
        self.rejected_calls = 0
        self.lock = threading.Lock()

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with bulkhead."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)

        return wrapper

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with bulkhead protection."""
        with self.lock:
            self.total_calls += 1

        # Try to acquire semaphore (non-blocking)
        acquired = self.semaphore.acquire(blocking=True, timeout=5)

        if not acquired:
            # Bulkhead is full
            with self.lock:
                self.rejected_calls += 1

            logger.warning(
                f"Bulkhead '{self.name}' is full, call rejected",
                extra={
                    "bulkhead": self.name,
                    "max_concurrent": self.max_concurrent,
                    "active_calls": self.active_calls,
                },
            )
            raise BulkheadFullException(
                f"Bulkhead '{self.name}' is full ({self.max_concurrent} concurrent calls)"
            )

        try:
            with self.lock:
                self.active_calls += 1

            result = func(*args, **kwargs)
            return result

        finally:
            with self.lock:
                self.active_calls -= 1
            self.semaphore.release()

    def get_stats(self) -> Dict[str, Any]:
        """Get bulkhead statistics."""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active_calls": self.active_calls,
            "total_calls": self.total_calls,
            "rejected_calls": self.rejected_calls,
            "utilization": (
                self.active_calls / self.max_concurrent * 100
                if self.max_concurrent > 0
                else 0
            ),
        }
