"""
Calendar API endpoints.
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.tenant import get_tenant_from_request
from app.core.security import get_current_user
from app.core.audit import AuditLogger
from app.models.user import User
from app.models.event import (
    Event,
    EventCreate,
    EventUpdate,
    EventResponse,
    EventType,
)
from app.services.calendar_service import CalendarService

router = APIRouter()


@router.get("", response_model=List[EventResponse])
async def list_events(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    event_type: Optional[EventType] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List calendar events for the current tenant.
    Supports filtering by date range and event type.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = CalendarService(db, tenant_id)
    events = await service.list_events(
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        limit=limit,
        offset=offset,
        user_id=str(user.id),
    )
    
    return events


@router.get("/today")
async def get_today_events(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get today's events.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = CalendarService(db, tenant_id)
    events = await service.get_today_events(str(user.id))
    
    return events


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    request: Request,
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific event by ID.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = CalendarService(db, tenant_id)
    event = await service.get_event(event_id, str(user.id))
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    return event


@router.post("", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new calendar event.
    If event type is 'meeting' or 'call', also creates an Appointment.
    """
    from app.models.event import EventType
    from app.models.office.office_models import Appointment, AppointmentStatus
    
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = CalendarService(db, tenant_id)
    event = await service.create_event(
        event_data=event_data.model_dump(),
        created_by_id=str(user.id),
    )
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.create(
        resource_type="event",
        resource_id=str(event.id),
        new_values=event.to_dict(),
    )
    
    # If this is a meeting or call, also create an Appointment
    if event_data.event_type in [EventType.MEETING, EventType.CALL]:
        # Check if appointment already exists for this event
        # Note: Appointment uses naive datetimes, Event uses timezone-aware
        # We need to normalize to UTC without timezone for comparison
        from datetime import timezone
        start_time_naive = event_data.start_time.astimezone(timezone.utc).replace(tzinfo=None)
        end_time_naive = event_data.end_time.astimezone(timezone.utc).replace(tzinfo=None)
        
        existing_apt = await db.execute(
            select(Appointment).where(
                Appointment.tenant_id == tenant_id,
                Appointment.title == event_data.title,
                Appointment.start_time == start_time_naive,
            )
        )
        if not existing_apt.scalar_one_or_none():
            appointment = Appointment(
                tenant_id=tenant_id,
                customer_id=None,  # Can be linked later
                assigned_to_id=str(user.id),
                title=event_data.title,
                description=event_data.description or "",
                location=event_data.location or "",
                start_time=start_time_naive,  # Store as naive UTC
                end_time=end_time_naive,  # Store as naive UTC
                status=AppointmentStatus.SCHEDULED,
                appointment_type=event_data.event_type.value,
            )
            db.add(appointment)
            await db.commit()
            # Update event with appointment reference
            event.appointment_id = str(appointment.id)
            await db.commit()
            await db.refresh(event)
    
    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    event_data: EventUpdate,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing event.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = CalendarService(db, tenant_id)
    
    # Get old values for audit
    old_event = await service.get_event(event_id, str(user.id))
    if not old_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    old_values = old_event.to_dict()
    
    event = await service.update_event(
        event_id=event_id,
        event_data=event_data.model_dump(exclude_unset=True),
        user_id=str(user.id),
    )
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.update(
        resource_type="event",
        resource_id=event_id,
        old_values=old_values,
        new_values=event.to_dict(),
    )
    
    return event


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an event.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = CalendarService(db, tenant_id)
    
    # Get old values for audit
    old_event = await service.get_event(event_id, str(user.id))
    if not old_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    await service.delete_event(event_id, str(user.id))
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.delete(
        resource_type="event",
        resource_id=event_id,
        old_values=old_event.to_dict(),
    )
    
    return {"message": "Event deleted successfully"}


@router.post("/{event_id}/sync")
async def sync_event_to_external(
    request: Request,
    event_id: str,
    provider: str = "microsoft",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync an event to external calendar (Microsoft/Google).
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = CalendarService(db, tenant_id)
    result = await service.sync_event_to_external(
        event_id=event_id,
        provider=provider,
        user_id=str(user.id),
    )
    
    return result
