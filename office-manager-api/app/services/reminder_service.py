"""
Reminder Service - Proactive appointment reminders and notifications

This service handles:
- 24-hour appointment reminders
- Follow-up notifications
- Multi-channel delivery (SMS, Email, Telegram)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.office.office_models import Appointment, AppointmentStatus, Customer, Employee
from app.services.email_service import send_email
from app.services.sms_service import send_sms
from app.integrations.telegram import send_telegram_message

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing appointment reminders and follow-ups."""
    
    # Reminder thresholds (hours before appointment)
    REMINDER_24H = 24
    REMINDER_2H = 2
    
    # Follow-up thresholds (days after appointment)
    FOLLOWUP_INVOICE = 7  # Days after appointment to follow up on payment
    FOLLOWUP_SATISFACTION = 3  # Days after appointment to check satisfaction
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_upcoming_appointments(
        self,
        hours_ahead: int = REMINDER_24H
    ) -> List[Appointment]:
        """Get appointments within the next N hours that need reminders."""
        now = datetime.utcnow()
        window_end = now + timedelta(hours=hours_ahead)
        
        query = select(Appointment).where(
            and_(
                Appointment.status == AppointmentStatus.CONFIRMED,
                Appointment.start_time >= now,
                Appointment.start_time <= window_end,
                Appointment.reminder_sent == False
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_appointments_needing_followup(
        self,
        days_after: int = FOLLOWUP_INVOICE
    ) -> List[Appointment]:
        """Get completed appointments needing follow-up."""
        cutoff = datetime.utcnow() - timedelta(days=days_after)
        
        query = select(Appointment).where(
            and_(
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.end_time <= cutoff,
                Appointment.followup_sent == False
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def send_appointment_reminder(
        self,
        appointment: Appointment,
        channel: str = "telegram"
    ) -> bool:
        """Send reminder for a specific appointment."""
        try:
            # Get customer info
            customer_query = select(Customer).where(Customer.id == appointment.customer_id)
            customer_result = await self.db.execute(customer_query)
            customer = customer_result.scalar_one_or_none()
            
            if not customer:
                logger.warning(f"Customer not found for appointment {appointment.id}")
                return False
            
            # Format reminder message
            message = self._format_reminder_message(appointment, customer)
            
            # Send via specified channel
            if channel == "telegram" and customer.telegram_chat_id:
                success = await send_telegram_message(
                    chat_id=customer.telegram_chat_id,
                    text=message
                )
            elif channel == "sms" and customer.phone:
                success = await send_sms(
                    to=customer.phone,
                    message=message
                )
            elif channel == "email" and customer.email:
                success = await send_email(
                    to=customer.email,
                    subject=f"Reminder: Appointment tomorrow - {appointment.title}",
                    body=message
                )
            else:
                logger.warning(f"No valid channel for customer {customer.id}")
                return False
            
            if success:
                # Mark reminder as sent
                appointment.reminder_sent = True
                appointment.reminder_sent_at = datetime.utcnow()
                await self.db.commit()
                logger.info(f"Reminder sent for appointment {appointment.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")
            return False
    
    def _format_reminder_message(
        self,
        appointment: Appointment,
        customer: Customer
    ) -> str:
        """Format reminder message for customer."""
        date_str = appointment.start_time.strftime("%A, %B %d at %I:%M %p")
        
        message = f"""
📅 Appointment Reminder

Hi {customer.contact_name or 'there'},

This is a friendly reminder about your upcoming appointment:

📋 {appointment.title}
📆 {date_str}
📍 {appointment.location or 'Location TBD'}

{appointment.description if appointment.description else ''}

Reply CONFIRM to confirm or CANCEL to cancel.

- The AI Office Manager
"""
        return message.strip()
    
    async def send_followup(
        self,
        appointment: Appointment,
        followup_type: str = "invoice"
    ) -> bool:
        """Send follow-up after appointment."""
        try:
            # Get customer info
            customer_query = select(Customer).where(Customer.id == appointment.customer_id)
            customer_result = await self.db.execute(customer_query)
            customer = customer_result.scalar_one_or_none()
            
            if not customer:
                return False
            
            if followup_type == "invoice":
                message = self._format_invoice_followup(appointment, customer)
                channel = "email"  # Usually email for invoices
            else:
                message = self._format_satisfaction_followup(appointment, customer)
                channel = "telegram"  # Telegram for quick feedback
            
            if channel == "telegram" and customer.telegram_chat_id:
                success = await send_telegram_message(
                    chat_id=customer.telegram_chat_id,
                    text=message
                )
            elif channel == "email" and customer.email:
                success = await send_email(
                    to=customer.email,
                    subject=f"How was your appointment? - {appointment.title}",
                    body=message
                )
            else:
                return False
            
            if success:
                appointment.followup_sent = True
                appointment.followup_sent_at = datetime.utcnow()
                await self.db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send follow-up: {e}")
            return False
    
    def _format_invoice_followup(
        self,
        appointment: Appointment,
        customer: Customer
    ) -> str:
        """Format invoice follow-up message."""
        return f"""
💰 Follow-Up: Invoice Reminder

Hi {customer.contact_name or 'there'},

We hope you had a great experience with us!

This is a friendly reminder that invoices for your recent appointment 
on {appointment.start_time.strftime('%B %d')} are now ready.

Please check your email for the detailed invoice.

If you have any questions, please don't hesitate to reach out.

Thank you for choosing us!

- The AI Office Manager
"""
    
    def _format_satisfaction_followup(
        self,
        appointment: Appointment,
        customer: Customer
    ) -> str:
        """Format satisfaction check follow-up."""
        return f"""
⭐ How Was Your Experience?

Hi {customer.contact_name or 'there'},

Thank you for visiting us on {appointment.start_time.strftime('%B %d')}!

We'd love to hear your feedback. How was your experience?

Please reply with:
- ⭐⭐⭐⭐⭐ - Excellent!
- ⭐⭐⭐⭐ - Good
- ⭐⭐⭐ - Average
- ⭐⭐ - Poor
- ⭐ - Very Poor

Your feedback helps us improve!

- The AI Office Manager
"""
    
    async def process_all_reminders(
        self,
        channel: str = "telegram"
    ) -> dict:
        """Process all pending reminders."""
        results = {
            "24h_reminders": {"sent": 0, "failed": 0},
            "2h_reminders": {"sent": 0, "failed": 0},
            "followups": {"sent": 0, "failed": 0}
        }
        
        # Process 24h reminders
        appointments_24h = await self.get_upcoming_appointments(hours_ahead=self.REMINDER_24H)
        for apt in appointments_24h:
            success = await self.send_appointment_reminder(apt, channel)
            if success:
                results["24h_reminders"]["sent"] += 1
            else:
                results["24h_reminders"]["failed"] += 1
        
        # Process 2h reminders
        appointments_2h = await self.get_upcoming_appointments(hours_ahead=self.REMINDER_2H)
        for apt in appointments_2h:
            # Skip if 24h reminder already sent
            if apt.reminder_sent:
                continue
            success = await self.send_appointment_reminder(apt, channel)
            if success:
                results["2h_reminders"]["sent"] += 1
            else:
                results["2h_reminders"]["failed"] += 1
        
        # Process follow-ups
        followups = await self.get_appointments_needing_followup()
        for apt in followups:
            success = await self.send_followup(apt)
            if success:
                results["followups"]["sent"] += 1
            else:
                results["followups"]["failed"] += 1
        
        logger.info(f"Reminder processing complete: {results}")
        return results


# Celery task for background processing
async def run_reminder_job():
    """Celery task to process all reminders."""
    from app.db.session import async_session_factory
    
    async with async_session_factory() as db:
        service = ReminderService(db)
        results = await service.process_all_reminders()
        return results


# Example usage
if __name__ == "__main__":
    import asyncio
    from app.db.session import async_session_factory
    
    async def main():
        async with async_session_factory() as db:
            service = ReminderService(db)
            results = await service.process_all_reminders()
            print(f"Reminder job results: {results}")
    
    asyncio.run(main())
