"""
Tests for circuit breaker functionality.
"""
import pytest
import asyncio
from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError


class TestCircuitBreaker:
    """Test suite for circuit breaker pattern."""
    
    @pytest.fixture
    def circuit(self):
        """Create a circuit breaker with test parameters."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for testing
            half_open_success_threshold=2,
        )
    
    @pytest.mark.asyncio
    async def test_circuit_allows_normal_requests(self, circuit):
        """Test that circuit allows requests when closed."""
        
        @circuit.call("test_service")
        async def successful_call():
            return "success"
        
        result = await successful_call()
        assert result == "success"
        
        # Verify state is still closed
        state = circuit.get_state("test_service")
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit):
        """Test that circuit opens after failure threshold is reached."""
        
        @circuit.call("test_service")
        async def failing_call():
            raise ValueError("Simulated failure")
        
        # Fail below threshold
        for i in range(2):
            with pytest.raises(ValueError):
                await failing_call()
        
        state = circuit.get_state("test_service")
        assert state["state"] == "closed"
        assert state["failure_count"] == 2
        
        # Fail to threshold
        with pytest.raises(ValueError):
            await failing_call()
        
        # Now circuit should be open
        state = circuit.get_state("test_service")
        assert state["state"] == "open"
        assert state["failure_count"] == 3
    
    @pytest.mark.asyncio
    async def test_circuit_blocks_requests_when_open(self, circuit):
        """Test that requests are blocked when circuit is open."""
        
        @circuit.call("test_service")
        async def failing_call():
            raise ValueError("Simulated failure")
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(ValueError):
                await failing_call()
        
        # Next call should raise CircuitOpenError
        with pytest.raises(CircuitOpenError) as exc_info:
            await failing_call()
        
        assert "test_service" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self, circuit):
        """Test that circuit transitions to half-open after recovery timeout."""
        
        @circuit.call("test_service")
        async def failing_call():
            raise ValueError("Simulated failure")
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(ValueError):
                await failing_call()
        
        # Wait for recovery timeout
        await asyncio.sleep(1.5)
        
        # Now request should be allowed (half-open state)
        # This call will reset the circuit if it succeeds
        try:
            await failing_call()
        except ValueError:
            pass  # Expected to fail again
        
        state = circuit.get_state("test_service")
        assert state["state"] in ["half_open", "closed"]
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_success(self, circuit):
        """Test that circuit closes after successful requests."""
        
        call_count = 0
        
        @circuit.call("test_service")
        async def sometimes_failing():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ValueError("Simulated failure")
            return "success"
        
        # Fail to open circuit
        for i in range(3):
            with pytest.raises(ValueError):
                await sometimes_failing()
        
        state = circuit.get_state("test_service")
        assert state["state"] == "open"
        
        # Wait for recovery
        await asyncio.sleep(1.5)
        
        # Succeed to transition to half-open
        result = await sometimes_failing()
        assert result == "success"
        
        # Need another success to fully close
        result = await sometimes_failing()
        assert result == "success"
        
        state = circuit.get_state("test_service")
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
    
    def test_sync_function_support(self, circuit):
        """Test that circuit breaker works with sync functions."""
        
        @circuit.call("sync_service")
        def sync_call():
            return "sync_success"
        
        result = sync_call()
        assert result == "sync_success"
    
    def test_multiple_services_independent(self, circuit):
        """Test that different services have independent circuits."""
        
        @circuit.call("service_a")
        async def call_a():
            raise ValueError("A failed")
        
        @circuit.call("service_b")
        async def call_b():
            return "B success"
        
        # Service A fails
        for i in range(3):
            with pytest.raises(ValueError):
                asyncio.run(call_a())
        
        # Service B should still work
        result = asyncio.run(call_b())
        assert result == "B success"
        
        # Service A circuit is open, B is closed
        state_a = circuit.get_state("service_a")
        state_b = circuit.get_state("service_b")
        
        assert state_a["state"] == "open"
        assert state_b["state"] == "closed"
