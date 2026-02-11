"""
Customer Portal Routes
HTML template rendering for customer-facing portal
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.db.session import get_db
from app.core.config import settings
from app.models.portal import CustomerUser
from app.models.office import Customer
from app.api.v1.portal.auth import get_current_customer_user

router = APIRouter(prefix="/portal", tags=["Customer Portal UI"])

# Templates
templates = Jinja2Templates(directory="app/templates/portal")


# ============ Page Routes ============

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: str = None
):
    """
    Render customer portal login page
    """
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": error,
            "current_user": None,
            "customer_company_name": None,
            "active_page": "login"
        }
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Render customer dashboard
    """
    # Get customer info
    customer_result = await db.execute(
        select(Customer).where(Customer.id == current_user.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    # Get dashboard stats
    from app.api.v1.portal.dashboard import get_dashboard_stats, get_recent_activity
    stats = await get_dashboard_stats(current_user, db)
    activity = await get_recent_activity(current_user, db)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "customer_company_name": customer.company_name if customer else "Customer",
            "active_page": "dashboard",
            "stats": stats.get("stats", {}),
            "recent_appointments": activity.get("recent_appointments", []),
            "recent_tasks": activity.get("recent_tasks", []),
            "recent_documents": activity.get("recent_documents", []),
        }
    )


@router.get("/appointments", response_class=HTMLResponse)
async def appointments_page(
    request: Request,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Render appointments page
    """
    from app.api.v1.portal.dashboard import get_customer_appointments
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == current_user.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    appointments_data = await get_customer_appointments(current_user, db=db)
    
    return templates.TemplateResponse(
        "appointments.html",
        {
            "request": request,
            "current_user": current_user,
            "customer_company_name": customer.company_name if customer else "Customer",
            "active_page": "appointments",
            "appointments": appointments_data.get("appointments", []),
        }
    )


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(
    request: Request,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Render projects page
    """
    from app.api.v1.portal.dashboard import get_customer_projects
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == current_user.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    projects_data = await get_customer_projects(current_user, db=db)
    
    return templates.TemplateResponse(
        "projects.html",
        {
            "request": request,
            "current_user": current_user,
            "customer_company_name": customer.company_name if customer else "Customer",
            "active_page": "projects",
            "projects": projects_data.get("projects", []),
        }
    )


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(
    request: Request,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Render tasks page
    """
    from app.api.v1.portal.dashboard import get_customer_tasks
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == current_user.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    tasks_data = await get_customer_tasks(current_user, db=db)
    
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "current_user": current_user,
            "customer_company_name": customer.company_name if customer else "Customer",
            "active_page": "tasks",
            "tasks": tasks_data.get("tasks", []),
        }
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(
    request: Request,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Render documents page
    """
    from app.api.v1.portal.dashboard import get_customer_documents
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == current_user.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    documents_data = await get_customer_documents(current_user, db=db)
    
    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
            "current_user": current_user,
            "customer_company_name": customer.company_name if customer else "Customer",
            "active_page": "documents",
            "documents": documents_data.get("documents", []),
        }
    )


@router.get("/time-entries", response_class=HTMLResponse)
async def time_entries_page(
    request: Request,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Render time entries page
    """
    from app.api.v1.portal.dashboard import get_customer_time_entries
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == current_user.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    time_data = await get_customer_time_entries(current_user, db=db)
    
    return templates.TemplateResponse(
        "time-entries.html",
        {
            "request": request,
            "current_user": current_user,
            "customer_company_name": customer.company_name if customer else "Customer",
            "active_page": "time",
            "time_entries": time_data.get("time_entries", []),
            "summary": time_data.get("summary", {}),
        }
    )


@router.get("/room-bookings", response_class=HTMLResponse)
async def room_bookings_page(
    request: Request,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Render room bookings page
    """
    from app.api.v1.portal.dashboard import get_customer_room_bookings
    
    customer_result = await db.execute(
        select(Customer).where(Customer.id == current_user.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    bookings_data = await get_customer_room_bookings(current_user, db=db)
    
    return templates.TemplateResponse(
        "room-bookings.html",
        {
            "request": request,
            "current_user": current_user,
            "customer_company_name": customer.company_name if customer else "Customer",
            "active_page": "bookings",
            "bookings": bookings_data.get("bookings", []),
        }
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: CustomerUser = Depends(get_current_customer_user)
):
    """
    Render settings page
    """
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "current_user": current_user,
            "customer_company_name": current_user.full_name,
            "active_page": "settings",
        }
    )
