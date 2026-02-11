"""
Customer Auto-Tagging Service - Intelligent customer classification

This service automatically tags customers based on their behavior:
- High-Value: Customers who spend above threshold
- At-Risk: Customers with no activity in X days
- New: Customers created within X days
- Loyal: Customers with multiple appointments
- Churned: Customers who haven't returned after threshold
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.office.office_models import Customer, Appointment
from app.models.user import User

logger = logging.getLogger(__name__)


class CustomerTagger:
    """Service for automatically tagging and classifying customers."""
    
    # Tag thresholds
    HIGH_VALUE_THRESHOLD = 1000  # Total spend $
    NO_ACTIVITY_DAYS = 90  # Days without activity = at-risk
    NEW_CUSTOMER_DAYS = 30  # Days since creation = new
    LOYAL_APPOINTMENTS = 5  # Number of appointments = loyal
    CHURNED_DAYS = 180  # Days without activity = churned
    
    # Tag names
    TAG_HIGH_VALUE = "high-value"
    TAG_AT_RISK = "at-risk"
    TAG_NEW = "new"
    TAG_LOYAL = "loyal"
    TAG_CHURNED = "churned"
    TAG_ACTIVE = "active"
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_customers(self) -> List[Customer]:
        """Get all customers for tagging."""
        query = select(Customer).where(Customer.is_active == True)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def analyze_customer(self, customer: Customer) -> List[str]:
        """Analyze a single customer and return applicable tags."""
        tags = []
        
        try:
            # Get customer statistics
            stats = await self.get_customer_stats(customer.id)
            
            # Check each tag condition
            if stats["total_spent"] >= self.HIGH_VALUE_THRESHOLD:
                tags.append(self.TAG_HIGH_VALUE)
            
            if stats["days_since_last_appointment"] <= self.NEW_CUSTOMER_DAYS:
                tags.append(self.TAG_NEW)
            elif stats["days_since_last_appointment"] >= self.CHURNED_DAYS:
                tags.append(self.TAG_CHURNED)
            elif stats["days_since_last_appointment"] >= self.NO_ACTIVITY_DAYS:
                tags.append(self.TAG_AT_RISK)
            
            if stats["total_appointments"] >= self.LOYAL_APPOINTMENTS:
                tags.append(self.TAG_LOYAL)
            
            if stats["days_since_last_appointment"] <= self.NO_ACTIVITY_DAYS:
                tags.append(self.TAG_ACTIVE)
            
        except Exception as e:
            logger.error(f"Error analyzing customer {customer.id}: {e}")
        
        return tags
    
    async def get_customer_stats(self, customer_id: UUID) -> Dict:
        """Get statistics for a customer."""
        # Get appointment count
        apt_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.customer_id == customer_id,
                Appointment.status == AppointmentStatus.COMPLETED
            )
        )
        apt_result = await self.db.execute(apt_query)
        total_appointments = apt_result.scalar() or 0
        
        # Get last appointment date
        last_apt_query = select(Appointment).where(
            and_(
                Appointment.customer_id == customer_id,
                Appointment.status == AppointmentStatus.COMPLETED
            )
        ).order_by(Appointment.end_time.desc()).limit(1)
        last_apt_result = await self.db.execute(last_apt_query)
        last_apt = last_apt_result.scalar_one_or_none()
        
        # Get days since last appointment
        if last_apt:
            days_since_last = (datetime.utcnow() - last_apt.end_time).days
            last_apt_date = last_apt.end_time
        else:
            days_since_last = 999  # Never had appointment
            last_apt_date = None
        
        # Get total spent (placeholder - would need Invoice model)
        total_spent = 0  # Would calculate from invoices
        
        return {
            "total_appointments": total_appointments,
            "days_since_last_appointment": days_since_last,
            "last_appointment_date": last_apt_date,
            "total_spent": total_spent,
            "is_new": days_since_last <= self.NEW_CUSTOMER_DAYS,
            "is_active": days_since_last <= self.NO_ACTIVITY_DAYS,
            "is_at_risk": days_since_last >= self.NO_ACTIVITY_DAYS and days_since_last < self.CHURNED_DAYS,
            "is_churned": days_since_last >= self.CHURNED_DAYS,
            "is_loyal": total_appointments >= self.LOYAL_APPOINTMENTS,
            "is_high_value": total_spent >= self.HIGH_VALUE_THRESHOLD
        }
    
    async def update_customer_tags(self, customer: Customer, tags: List[str]) -> bool:
        """Update customer tags in database."""
        try:
            # Merge new tags with existing, avoiding duplicates
            current_tags = customer.tags or []
            new_tags = set(current_tags) | set(tags)
            customer.tags = list(new_tags)
            customer.updated_at = datetime.utcnow()
            
            await self.db.commit()
            logger.info(f"Updated tags for customer {customer.id}: {tags}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating tags for customer {customer.id}: {e}")
            await self.db.rollback()
            return False
    
    async def process_all_customers(self) -> dict:
        """Analyze and tag all customers."""
        results = {
            "analyzed": 0,
            "tagged": 0,
            "errors": 0,
            "tag_distribution": {}
        }
        
        customers = await self.get_all_customers()
        
        for customer in customers:
            try:
                results["analyzed"] += 1
                tags = await self.analyze_customer(customer)
                
                if tags:
                    await self.update_customer_tags(customer, tags)
                    results["tagged"] += 1
                    
                    # Track tag distribution
                    for tag in tags:
                        results["tag_distribution"][tag] = results["tag_distribution"].get(tag, 0) + 1
                
            except Exception as e:
                logger.error(f"Error processing customer {customer.id}: {e}")
                results["errors"] += 1
        
        logger.info(f"Customer tagging complete: {results}")
        return results
    
    async def get_customers_by_tag(self, tag: str) -> List[Customer]:
        """Get all customers with a specific tag."""
        query = select(Customer).where(
            and_(
                Customer.is_active == True,
                Customer.tags.contains([tag])
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_at_risk_customers(self) -> List[Customer]:
        """Get all customers marked as at-risk."""
        return await self.get_customers_by_tag(self.TAG_AT_RISK)
    
    async def get_churned_customers(self) -> List[Customer]:
        """Get all customers marked as churned."""
        return await self.get_customers_by_tag(self.TAG_CHURNED)
    
    async def get_high_value_customers(self) -> List[Customer]:
        """Get all customers marked as high-value."""
        return await self.get_customers_by_tag(self.TAG_HIGH_VALUE)
    
    async def get_loyal_customers(self) -> List[Customer]:
        """Get all customers marked as loyal."""
        return await self.get_customers_by_tag(self.TAG_LOYAL)
    
    async def trigger_winback_campaign(self, customers: List[Customer]) -> dict:
        """Trigger win-back campaign for at-risk/churned customers."""
        results = {
            "targeted": len(customers),
            "notified": 0,
            "errors": 0
        }
        
        for customer in customers:
            try:
                # In production, this would trigger email/SMS campaign
                logger.info(f"Win-back campaign triggered for customer {customer.id}")
                results["notified"] += 1
            except Exception as e:
                logger.error(f"Error notifying customer {customer.id}: {e}")
                results["errors"] += 1
        
        return results


# Helper to avoid circular import
from app.models.office.office_models import AppointmentStatus


# Celery task for background processing
async def run_tagging_job():
    """Celery task to auto-tag all customers."""
    from app.db.session import async_session_factory
    
    async with async_session_factory() as db:
        tagger = CustomerTagger(db)
        results = await tagger.process_all_customers()
        return results


# Example usage
if __name__ == "__main__":
    import asyncio
    from app.db.session import async_session_factory
    
    async def main():
        async with async_session_factory() as db:
            tagger = CustomerTagger(db)
            
            # Process all customers
            results = await tagger.process_all_customers()
            print(f"Tagging results: {results}")
            
            # Get at-risk customers
            at_risk = await tagger.get_at_risk_customers()
            print(f"At-risk customers: {len(at_risk)}")
            
            # Trigger win-back for at-risk
            if at_risk:
                winback = await tagger.trigger_winback_campaign(at_risk)
                print(f"Win-back campaign: {winback}")
    
    asyncio.run(main())
