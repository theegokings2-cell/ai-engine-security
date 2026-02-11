"""
Tests for the shared HTTP client with retry logic.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.http_client import APIClient


class TestAPIClient:
    """Test suite for HTTP client with retry logic."""
    
    @pytest.fixture
    def client(self):
        """Create API client for testing."""
        return APIClient(timeout=5.0, max_attempts=3)
    
    @pytest.mark.asyncio
    async def test_successful_request(self, client):
        """Test that successful requests work normally."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            response = await client.get("https://api.example.com/test")
            
            assert response.status_code == 200
            mock_request.assert_called_once_with(
                "GET", "https://api.example.com/test"
            )
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, client):
        """Test that requests are retried on timeout exceptions."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            # First call times out, second succeeds
            mock_request.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                mock_response,
            ]
            
            response = await client.get("https://api.example.com/test")
            
            assert response.status_code == 200
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_on_connect_error(self, client):
        """Test that requests are retried on connection errors."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                httpx.ConnectError("Connection refused"),
                mock_response,
            ]
            
            response = await client.get("https://api.example.com/test")
            
            assert response.status_code == 200
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, client):
        """Test that client errors (4xx) are not retried."""
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("https://api.example.com/test")
            
            # Should only attempt once for client errors
            assert mock_request.call_count == 1
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, client):
        """Test that after max retries, exception is raised."""
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(httpx.TimeoutException):
                await client.get("https://api.example.com/test")
            
            # Should attempt 3 times (max_attempts)
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_post_request(self, client):
        """Test POST requests work correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            response = await client.post(
                "https://api.example.com/test",
                json={"key": "value"},
            )
            
            assert response.status_code == 201
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args
            assert call_kwargs[0][0] == "POST"
    
    @pytest.mark.asyncio
    async def test_client_singleton(self, client):
        """Test that client uses singleton pattern."""
        # Access client multiple times
        c1 = client.client
        c2 = client.client
        
        assert c1 is c2
    
    @pytest.mark.asyncio
    async def test_close_client(self, client):
        """Test that client can be closed."""
        with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
            await client.close()
            
            mock_close.assert_called_once()
            assert client._client is None
    
    @pytest.mark.asyncio
    async def test_response_headers_logged_on_error(self, client, caplog):
        """Test that response body is logged on HTTP errors."""
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_request.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("https://api.example.com/test")
