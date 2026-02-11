"""
Structured logging configuration for Office Manager API.
Uses structlog for consistent, structured log output.
"""
import structlog


def setup_logging() -> None:
    """Configure structlog for the application."""
    structlog.configure(
        processors=[
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Pre-configured logger instances for common use cases
def get_logger(name: str = None):
    """Get a configured logger instance."""
    return structlog.get_logger(name)


# Log enrichment helper for request context
class RequestContext:
    """Context manager for request-scoped log enrichment."""
    
    def __init__(self, request_id: str = None, tenant_id: str = None, user_id: str = None):
        self.request_id = request_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._log = None
    
    def __enter__(self):
        self._log = get_logger()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def log_action(self, action: str, status: str = "success", **extra):
        """Log an action with consistent fields."""
        log_data = {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "action": action,
            "status": status,
            **extra,
        }
        if status == "error":
            self._log.error(**log_data)
        else:
            self._log.info(**log_data)
        return log_data
