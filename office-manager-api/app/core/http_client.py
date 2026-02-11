"""
Shared HTTP client with timeouts and automatic retries.
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.logging import get_logger

logger = get_logger()


class APIClient:
    """Shared HTTP client with retry logic for external API calls."""
    
    def __init__(self, timeout: float = 30.0, max_attempts: int = 3):
        self.timeout = timeout
        self.max_attempts = max_attempts
        self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                http2=True,  # Enable HTTP/2 for better performance
            )
        return self._client
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Perform GET request with retry logic."""
        return await self._request_with_retry("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Perform POST request with retry logic."""
        return await self._request_with_retry("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Perform PUT request with retry logic."""
        return await self._request_with_retry("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Perform DELETE request with retry logic."""
        return await self._request_with_retry("DELETE", url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """Perform PATCH request with retry logic."""
        return await self._request_with_retry("PATCH", url, **kwargs)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=lambda retry_state: logger.warning(
            "retrying_http_request",
            url=retry_state.args[1] if len(retry_state.args) > 1 else "unknown",
            attempt=retry_state.attempt_number,
            exception=str(retry_state.outcome.exception),
        ),
    )
    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute request with retry logic for transient failures."""
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(
                "http_error",
                url=url,
                method=method,
                status=e.response.status_code,
                response_body=e.response.text[:500],
            )
            raise
        except httpx.RequestError as e:
            logger.error(
                "http_request_error",
                url=url,
                method=method,
                error=str(e),
            )
            raise
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instance for use across the application
http_client = APIClient()


async def get_http_client() -> APIClient:
    """Dependency to get the shared HTTP client."""
    return http_client
