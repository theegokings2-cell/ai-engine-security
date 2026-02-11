"""Quick test to debug customer creation."""
import asyncio
from uuid import UUID

# Import all models first to register relationships
import app.models  # noqa: F401

from app.db.session import async_session_factory
from app.models.office.office_models import Customer
from sqlalchemy import select, func

async def test_create():
    async with async_session_factory() as db:
        try:
            tenant_id = UUID("2c421ae2-3cb9-44ca-b7e3-3119f4828a50")

            # Test count query
            count_result = await db.execute(
                select(func.count(Customer.id)).where(Customer.tenant_id == tenant_id)
            )
            count = count_result.scalar() or 0
            print(f"Count: {count}")

            customer_number = f"CUST-{count + 1:06d}"
            print(f"Customer number: {customer_number}")

            # Create customer
            customer = Customer(
                tenant_id=tenant_id,
                customer_number=customer_number,
                company_name="TestCompany",
                customer_type="prospect",
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
            print(f"Created customer: {customer.id}")

            # Test model_dump
            dump = customer.model_dump()
            print(f"Model dump: {dump}")

        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_create())
