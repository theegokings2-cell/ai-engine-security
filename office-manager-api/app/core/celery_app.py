"""
Celery app configuration for background tasks.
Includes resilience settings for enterprise reliability.
"""
from celery import Celery
from celery.exceptions import MaxRetriesExceededError

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "office_manager",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Celery configuration for resilience
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=360,  # Hard limit: 6 minutes
    task_soft_time_limit=300,  # Soft limit: 5 minutes (triggers warning)
    
    # Message acknowledgment
    task_acks_late=True,  # Acknowledge after task completion (not before)
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    worker_disable_rate_limits=False,
    
    # Retry settings
    task_default_retry_delay=60,  # Default retry delay in seconds
    task_max_retries=3,  # Maximum retry attempts
    
    # Result expiration (1 hour)
    result_expires=3600,
    
    # Task routes
    task_routes={
        "app.services.*": {"queue": "default"},
        "app.integrations.*": {"queue": "integrations"},
        "app.integrations.email_tasks": {"queue": "email"},
        "app.integrations.sms_tasks": {"queue": "sms"},
    },
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        "check-reminders-every-minute": {
            "task": "app.services.reminder_tasks.check_and_send_reminders",
            "schedule": 60.0,  # Every minute
        },
        "cleanup-audit-logs-daily": {
            "task": "app.services.reminder_tasks.cleanup_old_audit_logs",
            "schedule": 86400.0,  # Daily
            "kwargs": {"days": 90},
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")
    return "Done"


# Import tasks to register them
from app.services import reminder_tasks  # noqa: F401


def make_idempotent_task(task_func):
    """
    Decorator to make Celery tasks idempotent.
    
    Usage:
        @celery_app.task(bind=True)
        @make_idempotent_task
        def my_task(self, idempotency_key=None, **kwargs):
            # Check if already processed
            result = check_idempotency(idempotency_key)
            if result:
                return result
            
            # Process task
            result = process_task(**kwargs)
            
            # Record completion
            save_idempotency(idempotency_key, result)
            return result
    """
    @task_func.__func__.task if hasattr(task_func, '__func__') else task_func
    def wrapper(*args, **kwargs):
        # The actual idempotency logic should be implemented in the task itself
        # This decorator just marks the task as requiring idempotency
        kwargs['_idempotent'] = True
        return task_func(*args, **kwargs)
    
    return wrapper
