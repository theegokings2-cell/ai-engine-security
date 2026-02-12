"""
Customer Portal API Endpoints
Simplified endpoints for customer portal users AND employees.
"""
from datetime import datetime
from typing import Optional, List, Union
from uuid import uuid4, UUID
import jwt

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.note import Note
from app.models.office.office_models import Appointment, AppointmentStatus, Customer
from app.models.portal import CustomerUser

router = APIRouter(prefix="/portal", tags=["Portal"])


# ============ Unified Auth for Portal ============

async def get_current_portal_user_v2(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> tuple[Optional[User], Optional[CustomerUser]]:
    """
    Get current authenticated user (either employee or customer).
    Returns (user, customer_user) - one will be None, the other populated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise credentials_exception
    
    token = auth_header[7:]
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.DecodeError, jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        raise credentials_exception
    
    portal_type = payload.get("portal_type")
    user_id = payload.get("sub")
    
    if user_id is None:
        raise credentials_exception
    
    # Check if employee token
    if portal_type == "employee":
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return (user, None)
        raise credentials_exception
    
    # Check if customer token (type: "access")
    if payload.get("type") == "access":
        customer_id = payload.get("customer_id")
        if customer_id:
            result = await db.execute(
                select(CustomerUser).where(
                    and_(
                        CustomerUser.id == user_id,
                        CustomerUser.customer_id == customer_id,
                        CustomerUser.is_active == True
                    )
                )
            )
            customer_user = result.scalar_one_or_none()
            if customer_user:
                return (None, customer_user)
    
    raise credentials_exception


# For backwards compatibility - just returns the User or CustomerUser
async def get_portal_user(
    user_tuple: tuple = Depends(get_current_portal_user_v2),
) -> Union[User, CustomerUser]:
    """Dependency that returns the authenticated user."""
    user, customer_user = user_tuple
    return user or customer_user


# ============ Helper Functions ============

def is_employee(user: Union[User, CustomerUser]) -> bool:
    """Check if the user is an employee."""
    return isinstance(user, User) and hasattr(user, 'role')


def get_customer_id(user: Union[User, CustomerUser]) -> Optional[UUID]:
    """Get the customer ID for filtering appointments."""
    if isinstance(user, CustomerUser):
        return user.customer_id
    return None


# ============== DASHBOARD ==============


# ============== DASHBOARD ==============

@router.get("/dashboard/stats")
async def get_portal_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, CustomerUser] = Depends(get_portal_user),
):
    """Get dashboard statistics for the current user (customer or employee)."""
    
    if isinstance(current_user, CustomerUser):
        # Customer: show their appointments
        customer_id = current_user.customer_id
        apt_result = await db.execute(
            select(Appointment).where(Appointment.customer_id == customer_id)
        )
        appointments = apt_result.scalars().all()
        
        now = datetime.utcnow()
        upcoming = [a for a in appointments if a.start_time and a.start_time > now]
        past = [a for a in appointments if a.start_time and a.start_time <= now]
        
        return {
            "user_type": "customer",
            "total_appointments": len(appointments),
            "upcoming_appointments": len(upcoming),
            "past_appointments": len(past),
            "completed_appointments": len([a for a in past if a.status == AppointmentStatus.COMPLETED]),
        }
    else:
        # Employee: show their work stats
        user_id = current_user.id
        
        # Count assigned appointments
        apt_result = await db.execute(
            select(Appointment).where(Appointment.assigned_to_id == user_id)
        )
        appointments = apt_result.scalars().all()

        now = datetime.utcnow()
        upcoming = [a for a in appointments if a.start_time and a.start_time > now]

        # Count active tasks
        task_result = await db.execute(
            select(Task).where(
                and_(
                    Task.assignee_id == user_id,
                    Task.status.in_(["pending", "in_progress"])
                )
            )
        )
        active_tasks = task_result.scalars().all()

        return {
            "user_type": "employee",
            "total_appointments": len(appointments),
            "upcoming_appointments": len(upcoming),
            "past_appointments": len([a for a in appointments if a.start_time and a.start_time <= now]),
            "active_tasks": len(active_tasks),
            "role": current_user.role,
        }


# ============== APPOINTMENTS ==============

@router.get("/appointments")
async def list_portal_appointments(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, CustomerUser] = Depends(get_portal_user),
):
    """List appointments for the current user (customer or employee)."""
    
    if isinstance(current_user, CustomerUser):
        # Customer: see appointments where they are the customer
        customer_id = current_user.customer_id
        query = select(Appointment).where(Appointment.customer_id == customer_id)
    else:
        # Employee: see appointments assigned to them
        user_id = current_user.id
        query = select(Appointment).where(Appointment.assigned_to_id == user_id)
    
    query = query.offset(skip).limit(limit).order_by(Appointment.start_time.desc())
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    appointment_list = []
    for apt in appointments:
        # Fetch customer data if exists
        customer_data = None
        if apt.customer_id:
            cust_result = await db.execute(
                select(Customer).where(Customer.id == apt.customer_id)
            )
            customer = cust_result.scalar_one_or_none()
            if customer:
                customer_data = {
                    "id": str(customer.id),
                    "company_name": customer.company_name,
                    "contact_name": customer.contact_name,
                    "email": customer.email,
                    "phone": customer.phone,
                }
        
        appointment_list.append({
            "id": str(apt.id),
            "title": apt.title,
            "description": apt.description,
            "customer_id": str(apt.customer_id) if apt.customer_id else None,
            "customer": customer_data,
            "start_time": apt.start_time.isoformat() if apt.start_time else None,
            "end_time": apt.end_time.isoformat() if apt.end_time else None,
            "status": apt.status.value if apt.status else "scheduled",
            "location": apt.location,
            "outcome": apt.outcome,
            "next_steps": apt.next_steps,
            "appointment_type": apt.appointment_type,
        })
    
    return {"appointments": appointment_list}


@router.post("/appointments")
async def create_portal_appointment(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_portal_user),
):
    """Create a new appointment."""
    
    if isinstance(current_user, CustomerUser):
        raise HTTPException(status_code=403, detail="Customers cannot create appointments")
    
    # Parse JSON body
    data = await request.json()
    title = data.get("title")
    description = data.get("description")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    customer_id = data.get("customer_id")
    location = data.get("location")
    notes = data.get("notes")
    status_value = data.get("status", "scheduled")
    
    if not title or not start_time or not end_time:
        raise HTTPException(status_code=400, detail="Title, start_time, and end_time are required")
    
    # Parse dates
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00")).replace(tzinfo=None)
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Validate customer if provided
    if customer_id:
        cust_result = await db.execute(
            select(Customer).where(
                and_(
                    Customer.id == customer_id,
                    Customer.tenant_id == current_user.tenant_id
                )
            )
        )
        customer = cust_result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
    
    from app.models.office.office_models import AppointmentStatus
    
    try:
        status_enum = AppointmentStatus(status_value.lower())
    except ValueError:
        status_enum = AppointmentStatus.SCHEDULED
    
    appointment = Appointment(
        id=uuid4(),
        title=title,
        description=description,
        start_time=start_dt,
        end_time=end_dt,
        customer_id=customer_id,
        location=location,
        status=status_enum,
        assigned_to_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    
    return {
        "id": str(appointment.id),
        "title": appointment.title,
        "description": appointment.description,
        "customer_id": str(appointment.customer_id) if appointment.customer_id else None,
        "start_time": appointment.start_time.isoformat() if appointment.start_time else None,
        "end_time": appointment.end_time.isoformat() if appointment.end_time else None,
        "status": appointment.status.value if appointment.status else "scheduled",
        "location": appointment.location,
    }


@router.put("/appointments/{appointment_id}")
async def update_portal_appointment(
    appointment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_portal_user),
):
    """Update an existing appointment."""

    if isinstance(current_user, CustomerUser):
        raise HTTPException(status_code=403, detail="Customers cannot update appointments")

    # Get the appointment first
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.id == appointment_id,
                Appointment.assigned_to_id == current_user.id
            )
        )
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Parse JSON body
    data = await request.json()
    title = data.get("title")
    description = data.get("description")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    customer_id = data.get("customer_id")
    location = data.get("location")
    notes = data.get("notes")
    status_value = data.get("status")

    # Update fields if provided
    if title:
        appointment.title = title
    if description is not None:
        appointment.description = description
    if start_time:
        try:
            appointment.start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")
    if end_time:
        try:
            appointment.end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")
    if location is not None:
        appointment.location = location
    if status_value:
        try:
            appointment.status = AppointmentStatus(status_value.lower())
        except ValueError:
            pass  # Keep existing status if invalid

    # Validate customer if provided
    if customer_id:
        cust_result = await db.execute(
            select(Customer).where(
                and_(
                    Customer.id == customer_id,
                    Customer.tenant_id == current_user.tenant_id
                )
            )
        )
        customer = cust_result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        appointment.customer_id = customer_id

    await db.commit()
    await db.refresh(appointment)

    return {
        "id": str(appointment.id),
        "title": appointment.title,
        "description": appointment.description,
        "customer_id": str(appointment.customer_id) if appointment.customer_id else None,
        "start_time": appointment.start_time.isoformat() if appointment.start_time else None,
        "end_time": appointment.end_time.isoformat() if appointment.end_time else None,
        "status": appointment.status.value if appointment.status else "scheduled",
        "location": appointment.location,
    }


@router.delete("/appointments/{appointment_id}")
async def delete_portal_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_portal_user),
):
    """Delete an appointment."""
    
    if isinstance(current_user, CustomerUser):
        raise HTTPException(status_code=403, detail="Customers cannot delete appointments")
    
    # Get appointment
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.id == appointment_id,
                Appointment.assigned_to_id == current_user.id
            )
        )
    )
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    await db.delete(appointment)
    await db.commit()
    
    return {"message": "Appointment deleted"}


@router.get("/appointments/{appointment_id}")
async def get_portal_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, CustomerUser] = Depends(get_portal_user),
):
    """Get a specific appointment."""
    
    if isinstance(current_user, CustomerUser):
        # Customer: only see their own appointments
        customer_id = current_user.customer_id
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.id == appointment_id,
                    Appointment.customer_id == customer_id
                )
            )
        )
    else:
        # Employee: see appointments assigned to them
        user_id = current_user.id
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.id == appointment_id,
                    Appointment.assigned_to_id == user_id
                )
            )
        )
    
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return {
        "id": str(appointment.id),
        "title": appointment.title,
        "description": appointment.description,
        "customer_id": str(appointment.customer_id) if appointment.customer_id else None,
        "start_time": appointment.start_time.isoformat() if appointment.start_time else None,
        "end_time": appointment.end_time.isoformat() if appointment.end_time else None,
        "status": appointment.status.value if appointment.status else "scheduled",
        "location": appointment.location,
        "outcome": appointment.outcome,
        "next_steps": appointment.next_steps,
        "appointment_type": appointment.appointment_type,
    }


# ============== CUSTOMERS (SELF) ==============

@router.get("/customers")
async def list_portal_customers(
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, CustomerUser] = Depends(get_portal_user),
):
    """List customers visible to this portal user."""
    
    if isinstance(current_user, CustomerUser):
        # Customer: only see their own customer record
        customer_id = current_user.customer_id
        result = await db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            return {"customers": []}
        
        return {
            "customers": [{
                "id": str(customer.id),
                "company_name": customer.company_name,
                "contact_name": customer.contact_name,
                "email": customer.email,
                "phone": customer.phone,
                "customer_type": customer.customer_type,
            }]
        }
    else:
        # Employee: see customers in their tenant
        tenant_id = current_user.tenant_id
        result = await db.execute(
            select(Customer).where(
                and_(
                    Customer.tenant_id == tenant_id,
                    Customer.is_active == True
                )
            ).limit(100)
        )
        customers = result.scalars().all()
        
        return {
            "customers": [{
                "id": str(c.id),
                "company_name": c.company_name,
                "contact_name": c.contact_name,
                "email": c.email,
                "phone": c.phone,
                "customer_type": c.customer_type,
            } for c in customers]
        }


# ============== TASKS ==============

from app.models.task import Task, TaskStatus, TaskPriority

@router.get("/tasks")
async def list_portal_tasks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, CustomerUser] = Depends(get_portal_user),
):
    """List tasks for the current user."""
    
    if isinstance(current_user, CustomerUser):
        # For customers, return empty for now
        return {"tasks": []}
    else:
        # Employee: see tasks assigned to them
        user_id = current_user.id
        result = await db.execute(
            select(Task).where(Task.assignee_id == user_id)
            .offset(skip).limit(limit).order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()
        
        return {
            "tasks": [{
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status.value if hasattr(t.status, 'value') else t.status,
                "priority": t.priority.value if hasattr(t.priority, 'value') else t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            } for t in tasks]
        }


@router.post("/tasks")
async def create_portal_task(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_portal_user),
):
    """Create a new task for the current employee."""
    
    if isinstance(current_user, CustomerUser):
        raise HTTPException(status_code=403, detail="Customers cannot create tasks")
    
    # Parse JSON body
    data = await request.json()
    title = data.get("title")
    description = data.get("description")
    priority = data.get("priority", "medium")
    due_date = data.get("due_date")
    
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    
    # Parse priority
    try:
        priority_enum = TaskPriority(priority.lower())
    except ValueError:
        priority_enum = TaskPriority.MEDIUM
    
    # Parse due date
    due_date_obj = None
    if due_date:
        try:
            due_date_obj = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    
    # Create task
    task = Task(
        id=uuid4(),
        title=title,
        description=description,
        priority=priority_enum,
        due_date=due_date_obj,
        status=TaskStatus.PENDING,
        assignee_id=current_user.id,
        creator_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "status": task.status.value if hasattr(task.status, 'value') else task.status,
        "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.put("/tasks/{task_id}/status")
async def update_portal_task_status(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_portal_user),
):
    """Update task status."""
    
    if isinstance(current_user, CustomerUser):
        raise HTTPException(status_code=403, detail="Customers cannot update tasks")
    
    # Parse JSON body
    data = await request.json()
    status_value = data.get("status")
    
    if not status_value:
        raise HTTPException(status_code=400, detail="Status is required")
    
    # Parse status
    try:
        status_enum = TaskStatus(status_value.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Get task
    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.assignee_id == current_user.id
            )
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = status_enum
    await db.commit()
    
    return {"message": "Task status updated", "status": status_value}


@router.delete("/tasks/{task_id}")
async def delete_portal_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_portal_user),
):
    """Delete a task."""
    
    if isinstance(current_user, CustomerUser):
        raise HTTPException(status_code=403, detail="Customers cannot delete tasks")
    
    # Get task
    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.creator_id == current_user.id
            )
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.delete(task)
    await db.commit()
    
    return {"message": "Task deleted"}


# ============== NOTES ==============

@router.get("/notes")
async def list_portal_notes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, CustomerUser] = Depends(get_portal_user),
):
    """List notes visible to this portal user."""
    
    if isinstance(current_user, CustomerUser):
        # For customers, return empty for now
        return {"notes": []}
    else:
        # Employee: see their own notes
        user_id = current_user.id
        result = await db.execute(
            select(Note).where(Note.created_by_id == user_id)
            .offset(skip).limit(limit).order_by(Note.created_at.desc())
        )
        notes = result.scalars().all()
        
        return {
            "notes": [{
                "id": str(n.id),
                "title": n.title,
                "content": n.content[:200] if n.content else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            } for n in notes]
        }


@router.post("/notes")
async def create_portal_note(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_portal_user),
):
    """Create a new note."""

    if isinstance(current_user, CustomerUser):
        raise HTTPException(status_code=403, detail="Customers cannot create notes")

    data = await request.json()
    title = data.get("title")
    content = data.get("content", "")

    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    note = Note(
        id=uuid4(),
        title=title,
        content=content,
        created_by_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }
