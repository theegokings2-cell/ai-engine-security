"""
Customer Portal Dashboard
Customer-facing endpoints for viewing company data, appointments, projects, etc.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.portal import CustomerUser
from app.models.office import (
    Customer, Appointment, PortalTask, TimeEntry,
    Document, RoomBooking, AppointmentStatus, TaskStatus,
)
from app.api.v1.portal.auth import get_current_customer_user

router = APIRouter(prefix="/portal/dashboard", tags=["Customer Portal Dashboard"])


# ============ Dashboard Stats ============

@router.get("/stats")
async def get_dashboard_stats(
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard statistics for customer
    """
    customer_id = current_user.customer_id
    
    # Get customer info
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    # Count appointments (next 7 days)
    week_from_now = datetime.utcnow() + timedelta(days=7)
    appointments_result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.customer_id == customer_id,
                Appointment.start_time >= datetime.utcnow(),
                Appointment.start_time <= week_from_now,
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.IN_PROGRESS
                ])
            )
        )
    )
    upcoming_appointments = appointments_result.scalar() or 0
    
    # Count active projects
    projects_result = await db.execute(
        select(func.count(Project.id)).where(
            and_(
                Project.tenant_id == customer.tenant_id if customer else None,
                Project.status.in_(["active", "planning", "in_progress"])
            )
        )
    )
    active_projects = projects_result.scalar() or 0
    
    # Count pending tasks
    tasks_result = await db.execute(
        select(func.count(PortalTask.id)).where(
            and_(
                PortalTask.tenant_id == customer.tenant_id if customer else None,
                PortalTask.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
            )
        )
    )
    pending_tasks = tasks_result.scalar() or 0
    
    # Count recent documents
    docs_result = await db.execute(
        select(func.count(Document.id)).where(
            and_(
                Document.tenant_id == customer.tenant_id if customer else None,
                Document.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        )
    )
    recent_documents = docs_result.scalar() or 0
    
    return {
        "stats": {
            "company_name": customer.company_name if customer else "Unknown",
            "upcoming_appointments": upcoming_appointments,
            "active_projects": active_projects,
            "pending_tasks": pending_tasks,
            "recent_documents": recent_documents,
        },
        "period": "next_7_days"
    }


@router.get("/activity")
async def get_recent_activity(
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activity for customer
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    tenant_id = customer.tenant_id if customer else None
    
    # Recent appointments
    appointments_result = await db.execute(
        select(Appointment)
        .where(Appointment.tenant_id == tenant_id)
        .order_by(Appointment.start_time.desc())
        .limit(5)
    )
    appointments = appointments_result.scalars().all()
    
    # Recent tasks
    tasks_result = await db.execute(
        select(PortalTask)
        .where(PortalTask.tenant_id == tenant_id)
        .order_by(PortalTask.updated_at.desc())
        .limit(5)
    )
    tasks = tasks_result.scalars().all()
    
    # Recent documents
    docs_result = await db.execute(
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
        .limit(5)
    )
    documents = docs_result.scalars().all()
    
    return {
        "recent_appointments": [
            {
                "id": str(a.id),
                "title": a.title,
                "start_time": a.start_time.isoformat() if a.start_time else None,
                "status": a.status,
                "assigned_to": a.assigned_to_id,
            }
            for a in appointments
        ],
        "recent_tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ],
        "recent_documents": [
            {
                "id": str(d.id),
                "name": d.name,
                "category": d.category,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in documents
        ],
    }


# ============ Appointments ============

@router.get("/appointments")
async def get_customer_appointments(
    current_user: CustomerUser = Depends(get_current_customer_user),
    upcoming: bool = True,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get appointments for customer
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    query = select(Appointment).where(Appointment.tenant_id == customer.tenant_id)
    
    if upcoming:
        query = query.where(
            and_(
                Appointment.start_time >= datetime.utcnow(),
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.IN_PROGRESS
                ])
            )
        ).order_by(Appointment.start_time.asc())
    else:
        query = query.order_by(Appointment.start_time.desc())
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    return {
        "appointments": [
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "location": a.location,
                "start_time": a.start_time.isoformat() if a.start_time else None,
                "end_time": a.end_time.isoformat() if a.end_time else None,
                "status": a.status,
                "type": a.appointment_type,
                "assigned_to": a.assigned_to_id,
            }
            for a in appointments
        ],
        "total": len(appointments)
    }


@router.get("/appointments/{appointment_id}")
async def get_appointment_details(
    appointment_id: str,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed appointment information
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.id == UUID(appointment_id),
                Appointment.tenant_id == customer.tenant_id
            )
        )
    )
    
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return {
        "appointment": {
            "id": str(appointment.id),
            "title": appointment.title,
            "description": appointment.description,
            "location": appointment.location,
            "start_time": appointment.start_time.isoformat() if appointment.start_time else None,
            "end_time": appointment.end_time.isoformat() if appointment.end_time else None,
            "status": appointment.status,
            "type": appointment.appointment_type,
            "outcome": appointment.outcome,
            "next_steps": appointment.next_steps,
        }
    }


# ============ Projects ============

@router.get("/projects")
async def get_customer_projects(
    current_user: CustomerUser = Depends(get_current_customer_user),
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get projects for customer
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    query = select(Project).where(Project.tenant_id == customer.tenant_id)
    
    if status_filter:
        query = query.where(Project.status == status_filter)
    
    query = query.order_by(Project.created_at.desc())
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return {
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "budget": p.budget,
            }
            for p in projects
        ],
        "total": len(projects)
    }


@router.get("/projects/{project_id}")
async def get_project_details(
    project_id: str,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed project information with tasks
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    # Get project
    project_result = await db.execute(
        select(Project).where(
            and_(
                Project.id == UUID(project_id),
                Project.tenant_id == customer.tenant_id
            )
        )
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get project tasks
    tasks_result = await db.execute(
        select(PortalTask).where(PortalTask.project_id == project.id)
    )
    tasks = tasks_result.scalars().all()
    
    return {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "budget": project.budget,
            "progress": sum(t.progress for t in tasks) / len(tasks) if tasks else 0,
        },
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "progress": t.progress,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ]
    }


# ============ Tasks ============

@router.get("/tasks")
async def get_customer_tasks(
    current_user: CustomerUser = Depends(get_current_customer_user),
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tasks for customer
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    query = select(PortalTask).where(PortalTask.tenant_id == customer.tenant_id)
    
    if status_filter:
        query = query.where(PortalTask.status == status_filter)
    
    query = query.order_by(PortalTask.due_date.asc().nullsfirst())
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "progress": t.progress,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "project_id": str(t.project_id) if t.project_id else None,
            }
            for t in tasks
        ],
        "total": len(tasks)
    }


# ============ Documents ============

@router.get("/documents")
async def get_customer_documents(
    current_user: CustomerUser = Depends(get_current_customer_user),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get documents available to customer
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    query = select(Document).where(
        and_(
            Document.tenant_id == customer.tenant_id,
            Document.is_public == True  # Only public documents
        )
    )
    
    if category:
        query = query.where(Document.category == category)
    
    query = query.order_by(Document.created_at.desc())
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return {
        "documents": [
            {
                "id": str(d.id),
                "name": d.name,
                "description": d.description,
                "category": d.category,
                "file_size": d.file_size,
                "mime_type": d.mime_type,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in documents
        ],
        "total": len(documents)
    }


# ============ Time Tracking ============

@router.get("/time-entries")
async def get_customer_time_entries(
    current_user: CustomerUser = Depends(get_current_customer_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get time entries for customer (billable time)
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    query = select(TimeEntry).where(
        and_(
            TimeEntry.tenant_id == customer.tenant_id,
            TimeEntry.billable == True
        )
    )
    
    if start_date:
        query = query.where(TimeEntry.date >= start_date)
    if end_date:
        query = query.where(TimeEntry.date <= end_date)
    
    query = query.order_by(TimeEntry.date.desc())
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # Calculate totals
    total_hours = sum(e.hours for e in entries if e.hours)
    billable_hours = sum(e.hours for e in entries if e.hours and e.billable)
    
    return {
        "time_entries": [
            {
                "id": str(e.id),
                "date": e.date.isoformat() if e.date else None,
                "hours": e.hours,
                "description": e.description,
                "billable": e.billable,
                "approved": e.approved,
            }
            for e in entries
        ],
        "summary": {
            "total_entries": len(entries),
            "total_hours": total_hours,
            "billable_hours": billable_hours,
        }
    }


# ============ Room Bookings ============

@router.get("/room-bookings")
async def get_customer_room_bookings(
    current_user: CustomerUser = Depends(get_current_customer_user),
    upcoming: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Get meeting room bookings for customer
    """
    customer_id = current_user.customer_id
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    query = select(RoomBooking).where(RoomBooking.tenant_id == customer.tenant_id)
    
    if upcoming:
        query = query.where(
            and_(
                RoomBooking.start_time >= datetime.utcnow(),
                RoomBooking.status != "cancelled"
            )
        ).order_by(RoomBooking.start_time.asc())
    else:
        query = query.order_by(RoomBooking.start_time.desc())
    
    result = await db.execute(query)
    bookings = result.scalars().all()
    
    return {
        "bookings": [
            {
                "id": str(b.id),
                "title": b.title,
                "description": b.description,
                "start_time": b.start_time.isoformat() if b.start_time else None,
                "end_time": b.end_time.isoformat() if b.end_time else None,
                "status": b.status,
                "attendees": b.attendees,
            }
            for b in bookings
        ],
        "total": len(bookings)
    }
