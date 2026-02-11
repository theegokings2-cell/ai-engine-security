"""
Reminder tasks for Celery background jobs.
Includes idempotency and resilience patterns.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from celery.exceptions import MaxRetriesExceededError

from app.core.celery_app import celery_app
from app.db.session import async_session_factory
from app.services.sms_service import SMSService
from app.services.email_service import EmailService
from app.core.logging import get_logger

logger = get_logger()


def generate_idempotency_key(prefix: str = "reminder") -> str:
    """Generate a unique idempotency key."""
    return f"{prefix}:{uuid.uuid4().hex}"


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    reject_on_worker_lost=True,
    task_time_limit=300,
    task_soft_time_limit=240,
)
def check_and_send_reminders(self):
    """
    Check for due reminders and send notifications.
    
    This task runs every minute via Celery Beat.
    
    Task is idempotent - processing the same reminder multiple times
    will not result in duplicate notifications.
    """
    import asyncio
    
    async def _check_reminders():
        async with async_session_factory() as db:
            from sqlalchemy import select, update
            from app.models.task import Task
            
            # Find tasks with due reminders
            now = datetime.utcnow()
            
            result = await db.execute(
                select(Task).where(
                    Task.reminder_enabled == "Y",
                    Task.reminder_sent == "N",
                    Task.reminder_at <= now,
                    Task.assignee_id.isnot(None),
                )
            )
            tasks = result.scalars().all()
            
            processed = []
            for task in tasks:
                # Generate idempotency key for this specific reminder
                idempotency_key = f"reminder:task:{task.id}:{task.reminder_at.isoformat()}"
                
                # Check if already processed (idempotency check)
                existing = await _check_idempotency(db, idempotency_key)
                if existing:
                    logger.info(
                        "reminder_already_processed",
                        task_id=str(task.id),
                        idempotency_key=idempotency_key,
                    )
                    processed.append({"task_id": str(task.id), "status": "skipped"})
                    continue
                
                # Get assignee (simplified - in production, query user table)
                channel = task.reminder_channel
                recipient = task.assignee_email  # Placeholder
                
                if channel in ["email", "sms", "telegram"]:
                    # Queue individual notification task
                    send_reminder_notification.delay(
                        task_id=str(task.id),
                        channel=channel,
                        recipient=recipient,
                        idempotency_key=idempotency_key,
                    )
                
                processed.append({"task_id": str(task.id), "status": "queued"})
            
            await db.commit()
            return {"tasks_processed": len(processed), "details": processed}
    
    try:
        result = asyncio.run(_check_reminders())
        logger.info("check_reminders_completed", **result)
        return result
    except Exception as e:
        logger.error("check_reminders_failed", error=str(e))
        raise


async def _check_idempotency(db, idempotency_key: str) -> bool:
    """Check if an idempotency key already exists."""
    from sqlalchemy import select
    from app.models.audit_log import AuditLog
    
    result = await db.execute(
        select(AuditLog).where(AuditLog.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none() is not None


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_reminder_notification(
    self,
    task_id: str,
    channel: str,
    recipient: str,
    idempotency_key: Optional[str] = None,
):
    """
    Send a reminder notification via the specified channel.
    
    Args:
        task_id: The task ID to remind about
        channel: email, sms, or telegram
        recipient: The recipient address/phone/chat_id
        idempotency_key: Unique key for idempotency (auto-generated if not provided)
    
    Task is idempotent - same idempotency_key will only send once.
    """
    import asyncio
    
    if idempotency_key is None:
        idempotency_key = f"reminder:send:{task_id}:{channel}:{recipient}"
    
    async def _send():
        async with async_session_factory() as db:
            from sqlalchemy import select
            from app.models.task import Task
            from app.models.audit_log import AuditLog
            
            # Idempotency check
            existing = await db.execute(
                select(AuditLog).where(AuditLog.idempotency_key == idempotency_key)
            )
            if existing.scalar_one_or_none():
                logger.info(
                    "notification_already_sent",
                    idempotency_key=idempotency_key,
                    task_id=task_id,
                )
                return {"status": "already_sent", "task_id": task_id, "channel": channel}
            
            result = await db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                logger.warning("task_not_found", task_id=task_id)
                return {"status": "error", "message": "Task not found"}
            
            message = f"Reminder: {task.title}"
            if task.due_date:
                message += f" (Due: {task.due_date.isoformat()})"
            
            result_data = None
            
            if channel == "email":
                email_service = EmailService(db, str(task.tenant_id))
                result_data = await email_service.send_email(
                    to=[recipient],
                    subject=f"Task Reminder: {task.title}",
                    body=message,
                )
            elif channel == "sms":
                sms_service = SMSService(db, str(task.tenant_id))
                result_data = await sms_service.send_sms(to=recipient, body=message)
            elif channel == "telegram":
                # Telegram integration placeholder
                result_data = {"status": "stub", "message": "Telegram not implemented"}
            else:
                result_data = {"status": "error", "message": f"Unknown channel: {channel}"}
            
            # Record idempotency
            audit = AuditLog(
                tenant_id=task.tenant_id,
                action="reminder_sent",
                idempotency_key=idempotency_key,
                details={
                    "task_id": task_id,
                    "channel": channel,
                    "result": result_data,
                },
            )
            db.add(audit)
            await db.commit()
            
            return {
                "status": "sent",
                "task_id": task_id,
                "channel": channel,
                "result": result_data,
            }
    
    try:
        result = asyncio.run(_send())
        logger.info("reminder_sent", **result)
        return result
    except Exception as e:
        logger.error("reminder_send_failed", error=str(e), task_id=task_id)
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
    acks_late=True,
    task_time_limit=600,  # 10 minutes for cleanup
)
def cleanup_old_audit_logs(self, days: int = 90):
    """
    Clean up audit logs older than specified days.
    
    Args:
        days: Number of days to retain (default: 90)
    """
    import asyncio
    
    async def _cleanup():
        async with async_session_factory() as db:
            from sqlalchemy import delete
            from app.models.audit_log import AuditLog
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Get count before deletion
            from sqlalchemy import func
            count_result = await db.execute(
                select(func.count(AuditLog.id)).where(AuditLog.created_at < cutoff)
            )
            count = count_result.scalar() or 0
            
            # Delete old logs
            await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff)
            )
            await db.commit()
            
            return {"status": "completed", "days_retained": days, "deleted_count": count}
    
    try:
        result = asyncio.run(_cleanup())
        logger.info("audit_cleanup_completed", **result)
        return result
    except Exception as e:
        logger.error("audit_cleanup_failed", error=str(e))
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
    acks_late=True,
)
def sync_calendar_events(self, provider: str = "microsoft"):
    """
    Sync calendar events from external provider.
    
    Args:
        provider: microsoft or google
    """
    import asyncio
    
    async def _sync():
        async with async_session_factory() as db:
            # Placeholder for calendar sync
            # In production, this would:
            # 1. Fetch events from external calendar API
            # 2. Match events to existing tasks/meetings
            # 3. Update local records
            # 4. Handle conflicts
            pass
    
    try:
        result = asyncio.run(_sync())
        logger.info("calendar_sync_completed", provider=provider)
        return {"status": "completed", "provider": provider}
    except Exception as e:
        logger.error("calendar_sync_failed", error=str(e), provider=provider)
        raise


# Import sqlalchemy select for the cleanup function
from sqlalchemy import select
