"""
Circuit breaker pattern for external service resilience.
Prevents cascading failures by stopping requests to failing services.
"""
from functools import wraps
import time
from typing import Optional


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for managing external service calls.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are blocked
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        self.failures = {}  # service_name -> failure_count
        self.last_failure = {}  # service_name -> timestamp
        self.successes = {}  # service_name -> success_count (for half-open state)
        self.state = {}  # service_name -> 'closed' | 'open' | 'half_open'
    
    def call(self, service_name: str):
        """
        Decorator to wrap functions with circuit breaker protection.
        
        Args:
            service_name: Name of the external service
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if self._is_open(service_name):
                    raise CircuitOpenError(
                        f"Circuit is open for service '{service_name}'. "
                        f"Requests blocked for {self.recovery_timeout}s after failure threshold."
                    )
                
                try:
                    result = await func(*args, **kwargs)
                    self._on_success(service_name)
                    return result
                except Exception as e:
                    self._on_failure(service_name)
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if self._is_open(service_name):
                    raise CircuitOpenError(
                        f"Circuit is open for service '{service_name}'. "
                        f"Requests blocked for {self.recovery_timeout}s after failure threshold."
                    )
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success(service_name)
                    return result
                except Exception as e:
                    self._on_failure(service_name)
                    raise
            
            # Return async wrapper if function is async
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return wrapper
            return sync_wrapper
        
        return decorator
    
    def _is_open(self, service_name: str) -> bool:
        """Check if circuit is open for the service."""
        if service_name not in self.state:
            return False
        
        if self.state[service_name] == 'open':
            # Check if recovery timeout has elapsed
            if service_name in self.last_failure:
                elapsed = time.time() - self.last_failure[service_name]
                if elapsed >= self.recovery_timeout:
                    # Transition to half_open
                    self.state[service_name] = 'half_open'
                    self.successes[service_name] = 0
                    return False
            return True
        
        return self.state[service_name] == 'open'
    
    def _on_success(self, service_name: str) -> None:
        """Handle successful request."""
        if self.state.get(service_name) == 'half_open':
            self.successes[service_name] = self.successes.get(service_name, 0) + 1
            if self.successes[service_name] >= self.half_open_success_threshold:
                # Circuit recovered
                self._reset(service_name)
    
    def _on_failure(self, service_name: str) -> None:
        """Handle failed request."""
        self.failures[service_name] = self.failures.get(service_name, 0) + 1
        self.last_failure[service_name] = time.time()
        
        if self.failures[service_name] >= self.failure_threshold:
            self.state[service_name] = 'open'
    
    def _reset(self, service_name: str) -> None:
        """Reset circuit breaker for a service."""
        self.failures.pop(service_name, None)
        self.last_failure.pop(service_name, None)
        self.successes.pop(service_name, None)
        self.state.pop(service_name, None)
    
    def get_state(self, service_name: str) -> dict:
        """Get current state of circuit breaker for a service."""
        return {
            "service": service_name,
            "state": self.state.get(service_name, "closed"),
            "failure_count": self.failures.get(service_name, 0),
            "last_failure": self.last_failure.get(service_name),
        }


# Global circuit breaker instance
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    half_open_success_threshold=2,
)
