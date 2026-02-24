"""
Circuit Breaker Pattern
Prevents cascade failures when external services are down
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, requests rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: float = 30.0,
        reset_timeout_seconds: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.reset_timeout_seconds = reset_timeout_seconds
        
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self._state_changed_at = time.time()
        self._lock = asyncio.Lock()
    
    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try resetting."""
        if self.state != CircuitState.OPEN:
            return False
        return time.time() - self._state_changed_at >= self.reset_timeout_seconds
    
    async def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self._state_changed_at = time.time()
            logger.info(f"Circuit {self.name}: {old_state.value} -> {new_state.value}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        Raises CircuitOpenError if circuit is open.
        """
        async with self._lock:
            # Check if we should try to reset
            if self._should_attempt_reset():
                await self._transition_to(CircuitState.HALF_OPEN)
            
            # Reject if open
            if self.state == CircuitState.OPEN:
                raise CircuitOpenError(f"Circuit {self.name} is open")
        
        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout_seconds
                )
            else:
                result = func(*args, **kwargs)
            
            await self._on_success()
            return result
            
        except asyncio.TimeoutError:
            await self._on_failure("Timeout")
            raise
        except Exception as e:
            await self._on_failure(str(e))
            raise
    
    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            self.stats.successes += 1
            self.stats.last_success_time = time.time()
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            
            if self.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
    
    async def _on_failure(self, error: str):
        """Handle failed call."""
        async with self._lock:
            self.stats.failures += 1
            self.stats.last_failure_time = time.time()
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            
            if self.state == CircuitState.HALF_OPEN:
                await self._transition_to(CircuitState.OPEN)
            elif self.state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)
    
    def get_status(self) -> dict:
        """Get current circuit status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.stats.failures,
            "successes": self.stats.successes,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure": self.stats.last_failure_time,
            "last_success": self.stats.last_success_time,
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breakers for external services
_circuits: Dict[str, CircuitBreaker] = {}


def get_circuit(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker."""
    if name not in _circuits:
        _circuits[name] = CircuitBreaker(name, **kwargs)
    return _circuits[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout_seconds: float = 30.0,
):
    """
    Decorator to wrap a function with a circuit breaker.
    
    Usage:
        @circuit_breaker("twilio")
        async def send_sms(phone, message):
            ...
    """
    def decorator(func: Callable):
        circuit = get_circuit(
            name,
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds,
        )
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit.call(func, *args, **kwargs)
        
        # Attach circuit for inspection
        wrapper.circuit = circuit
        return wrapper
    
    return decorator


def get_all_circuit_status() -> Dict[str, dict]:
    """Get status of all circuit breakers."""
    return {name: circuit.get_status() for name, circuit in _circuits.items()}


# Pre-configured circuits for common services
twilio_circuit = get_circuit("twilio", failure_threshold=3, timeout_seconds=10)
anthropic_circuit = get_circuit("anthropic", failure_threshold=5, timeout_seconds=60)
hubspot_circuit = get_circuit("hubspot", failure_threshold=3, timeout_seconds=15)
sendgrid_circuit = get_circuit("sendgrid", failure_threshold=3, timeout_seconds=10)
