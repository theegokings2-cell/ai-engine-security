"""
Office Management API Endpoints
Comprehensive office management: departments, employees, locations, rooms, resources, customers, appointments, time tracking, and attendance.
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user

# Import full models package to register all SQLAlchemy relationships
import app.models  # noqa: F401

from app.models.user import User
from app.models.office.office_models import (
    Department, Employee, Location, MeetingRoom, Resource,
    RoomBooking, ResourceBooking, Customer, CustomerContact,
    Appointment, TimeEntry, Attendance,
    BookingStatus, AppointmentStatus,
)

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint - no auth required."""
    return {"status": "ok", "message": "Office API is working"}


# ============== DEPARTMENTS ==============

@router.get("/departments")
async def list_departments(
    search: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all departments."""
    query = select(Department).where(Department.tenant_id == user.tenant_id)
    
    if is_active is not None:
        query = query.where(Department.is_active == is_active)
    
    if search:
        query = query.where(Department.name.ilike(f"%{search}%"))
    
    query = query.offset(skip).limit(limit).order_by(Department.name)
    result = await db.execute(query)
    departments = result.scalars().all()
    
    return {"departments": [d.model_dump() for d in departments]}


@router.get("/departments/enterprise")
async def list_enterprise_departments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns enterprise-level departments including core divisions
    of a multi-billion dollar organization.
    """
    # Enterprise department structure
    enterprise_departments = [
        # Executive
        {"id": "exec", "name": "Executive", "description": "C-Suite leadership and executive team"},
        {"id": "ceo-office", "name": "CEO Office", "description": "Chief Executive Officer operations"},
        
        # Operations
        {"id": "operations", "name": "Operations", "description": "Core business operations"},
        {"id": "supply-chain", "name": "Supply Chain", "description": "Logistics and procurement"},
        {"id": "manufacturing", "name": "Manufacturing", "description": "Production and manufacturing"},
        {"id": "quality-assurance", "name": "Quality Assurance", "description": "Product and service quality"},
        
        # Finance
        {"id": "finance", "name": "Finance", "description": "Financial management and reporting"},
        {"id": "accounting", "name": "Accounting", "description": "Bookkeeping and financial records"},
        {"id": "treasury", "name": "Treasury", "description": "Cash and investment management"},
        {"id": "investor-relations", "name": "Investor Relations", "description": "Shareholder communications"},
        {"id": "tax", "name": "Tax", "description": "Tax planning and compliance"},
        
        # Sales & Marketing
        {"id": "sales", "name": "Sales", "description": "Revenue generation and client acquisition"},
        {"id": "marketing", "name": "Marketing", "description": "Brand management and campaigns"},
        {"id": "product", "name": "Product", "description": "Product development and management"},
        {"id": "business-development", "name": "Business Development", "description": "Strategic partnerships"},
        {"id": "customer-success", "name": "Customer Success", "description": "Client retention and growth"},
        
        # Technology
        {"id": "technology", "name": "Technology", "description": "IT infrastructure and operations"},
        {"id": "engineering", "name": "Engineering", "description": "Research and development"},
        {"id": "software-dev", "name": "Software Development", "description": "Application development"},
        {"id": "data-analytics", "name": "Data & Analytics", "description": "Business intelligence and data science"},
        {"id": "cybersecurity", "name": "Cybersecurity", "description": "Information security"},
        {"id": "cloud-ops", "name": "Cloud Operations", "description": "Cloud infrastructure management"},
        
        # Human Resources
        {"id": "human-resources", "name": "Human Resources", "description": "HR operations and employee services"},
        {"id": "talent-acquisition", "name": "Talent Acquisition", "description": "Recruitment and hiring"},
        {"id": "people-ops", "name": "People Operations", "description": "Employee experience and culture"},
        {"id": "learning-development", "name": "Learning & Development", "description": "Training and career growth"},
        {"id": "compensation-benefits", "name": "Compensation & Benefits", "description": "Pay and benefits administration"},
        
        # Legal & Compliance
        {"id": "legal", "name": "Legal", "description": "Legal affairs and counsel"},
        {"id": "compliance", "name": "Compliance", "description": "Regulatory compliance"},
        {"id": "risk-management", "name": "Risk Management", "description": "Enterprise risk assessment"},
        {"id": "corporate-secretary", "name": "Corporate Secretary", "description": "Governance and board relations"},
        
        # Corporate Services
        {"id": "facilities", "name": "Facilities", "description": "Office and workplace management"},
        {"id": "real-estate", "name": "Real Estate", "description": "Property and lease management"},
        {"id": "procurement", "name": "Procurement", "description": "Vendor management and purchasing"},
        {"id": "security", "name": "Security", "description": "Physical and corporate security"},
        {"id": "events", "name": "Corporate Events", "description": "Internal and external events"},
        
        # Strategy & Planning
        {"id": "strategy", "name": "Strategy", "description": "Corporate strategy and planning"},
        {"id": "corporate-development", "name": "Corporate Development", "description": "M&A and strategic initiatives"},
        {"id": "planning-budgeting", "name": "Planning & Budgeting", "description": "Financial planning and budgeting"},
        
        # Communications
        {"id": "corporate-communications", "name": "Corporate Communications", "description": "Internal and external messaging"},
        {"id": "public-relations", "name": "Public Relations", "description": "Media relations and PR"},
        {"id": "government-relations", "name": "Government Relations", "description": "Policy and government affairs"},
        
        # Customer Service
        {"id": "customer-service", "name": "Customer Service", "description": "Client support and service"},
        {"id": "technical-support", "name": "Technical Support", "description": "Technical helpdesk and support"},
        {"id": "call-center", "name": "Call Center", "description": "Phone-based customer service"},
    ]
    
    # Get existing departments
    query = select(Department).where(Department.tenant_id == user.tenant_id)
    result = await db.execute(query)
    existing_depts = result.scalars().all()
    existing_names = {d.name.lower() for d in existing_depts}
    
    # Merge enterprise departments with existing ones
    all_departments = []
    seen_ids = set()
    
    # First add enterprise departments (if not exists)
    for dept in enterprise_departments:
        if dept["name"].lower() not in existing_names:
            all_departments.append({
                **dept,
                "is_default": True,
                "description": dept.get("description", ""),
            })
    
    # Then add custom departments
    for d in existing_depts:
        all_departments.append({
            "id": str(d.id),
            "name": d.name,
            "description": d.description or "",
            "is_default": False,
        })
    
    return {"departments": all_departments}


@router.post("/departments")
async def create_department(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new department."""
    department = Department(
        tenant_id=user.tenant_id,
        name=name,
        description=description,
        parent_id=UUID(parent_id) if parent_id else None,
    )
    db.add(department)
    await db.commit()
    await db.refresh(department)
    
    return {"department": department.model_dump(), "message": "Department created successfully"}


# ============== EMPLOYEES ==============

@router.get("/employees")
async def list_employees(
    search: Optional[str] = None,
    department_id: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all employees."""
    from sqlalchemy.orm import selectinload

    query = select(Employee).where(Employee.tenant_id == user.tenant_id)

    if is_active is not None:
        query = query.where(Employee.is_active == is_active)

    if department_id:
        query = query.where(Employee.department_id == UUID(department_id))

    if search:
        query = query.where(
            or_(
                Employee.employee_id.ilike(f"%{search}%"),
                Employee.user.has(User.email.ilike(f"%{search}%")),
            )
        )

    # Eager load user and department relationships
    query = query.options(selectinload(Employee.user), selectinload(Employee.department))
    query = query.offset(skip).limit(limit).order_by(Employee.created_at.desc())
    result = await db.execute(query)
    employees = result.scalars().all()

    # Include user info in response
    employee_list = []
    for e in employees:
        emp_data = e.model_dump()
        if e.user:
            emp_data["user"] = {
                "id": str(e.user.id),
                "email": e.user.email,
                "full_name": e.user.full_name,
            }
        if e.department:
            emp_data["department"] = {
                "id": str(e.department.id),
                "name": e.department.name,
            }
        employee_list.append(emp_data)

    return {"employees": employee_list}


@router.post("/employees")
async def create_employee(
    user_id: str,
    employee_id: str,
    department_id: Optional[str] = None,
    job_title: Optional[str] = None,
    phone: Optional[str] = None,
    hire_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create employee profile."""
    # Verify user exists
    user = await db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for existing employee profile
    existing = await db.execute(
        select(Employee).where(
            and_(
                Employee.user_id == UUID(user_id),
                Employee.tenant_id == current_user.tenant_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Employee profile already exists")
    
    employee = Employee(
        tenant_id=current_user.tenant_id,
        user_id=UUID(user_id),
        employee_id=employee_id,
        department_id=UUID(department_id) if department_id else None,
        job_title=job_title,
        phone=phone,
        hire_date=hire_date,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    
    return {"employee": employee.model_dump(), "message": "Employee profile created"}


@router.post("/employees/with-user")
async def create_employee_with_user(
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    employee_id: str = Form(...),
    department_id: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    hire_date: Optional[str] = Form(None),  # Receive as string, parse manually
    role: str = Form("employee"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create both a User account and Employee profile in one step.
    This is the preferred way to add new employees.
    """
    import bcrypt
    from app.models.user import UserRole
    
    # Check if user with email already exists
    existing_user = await db.execute(
        select(User).where(User.email == email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Parse hire_date manually if provided
    hire_date_parsed = None
    if hire_date:
        try:
            hire_date_parsed = datetime.fromisoformat(hire_date)
        except (ValueError, TypeError):
            hire_date_parsed = None
    
    # Hash password with bcrypt directly (avoiding passlib compatibility issues)
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        # Create User account
        user = User(
            tenant_id=current_user.tenant_id,
            email=email,
            hashed_password=hashed_pw,
            full_name=full_name,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        db.add(user)
        await db.flush()  # Get the user ID

        # Create Employee profile linked to user
        employee = Employee(
            tenant_id=current_user.tenant_id,
            user_id=user.id,
            employee_id=employee_id,
            department_id=UUID(department_id) if department_id else None,
            job_title=job_title,
            phone=phone,
            hire_date=hire_date_parsed,
            is_active=True,
        )
        db.add(employee)
        await db.commit()
        await db.refresh(employee)
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig) if e.orig else str(e)
        if "employee_id" in error_msg:
            raise HTTPException(status_code=409, detail=f"Employee ID '{employee_id}' already exists")
        elif "email" in error_msg:
            raise HTTPException(status_code=409, detail=f"Email '{email}' already exists")
        raise HTTPException(status_code=409, detail="A record with these details already exists")

    employee_data = employee.model_dump()
    employee_data["user"] = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
    }

    return {
        "employee": employee_data,
        "user": {"id": str(user.id), "email": user.email, "full_name": user.full_name},
        "message": "User and employee created successfully"
    }


@router.delete("/employees/{employee_id}")
async def delete_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete an employee (soft delete - sets is_active to false)."""
    employee = await db.get(Employee, UUID(employee_id))
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Soft delete - just mark as inactive
    employee.is_active = False
    await db.commit()
    await db.refresh(employee)

    return {"message": "Employee deleted successfully"}


# ============== LOCATIONS ==============

@router.get("/locations")
async def list_locations(
    search: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all office locations."""
    query = select(Location).where(Location.tenant_id == user.tenant_id)
    
    if is_active is not None:
        query = query.where(Location.is_active == is_active)
    
    if search:
        query = query.where(Location.name.ilike(f"%{search}%"))
    
    query = query.offset(skip).limit(limit).order_by(Location.name)
    result = await db.execute(query)
    locations = result.scalars().all()
    
    return {"locations": [l.model_dump() for l in locations]}


@router.post("/locations")
async def create_location(
    name: str,
    address: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    postal_code: Optional[str] = None,
    phone: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new office location."""
    location = Location(
        tenant_id=user.tenant_id,
        name=name,
        address=address,
        city=city,
        state=state,
        country=country,
        postal_code=postal_code,
        phone=phone,
    )
    db.add(location)
    await db.commit()
    await db.refresh(location)
    
    return {"location": location.model_dump(), "message": "Location created successfully"}


# ============== MEETING ROOMS ==============

@router.get("/rooms")
async def list_rooms(
    location_id: Optional[str] = None,
    capacity_min: Optional[int] = None,
    amenities: Optional[List[str]] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all meeting rooms."""
    query = select(MeetingRoom).where(MeetingRoom.tenant_id == user.tenant_id)
    
    if is_active is not None:
        query = query.where(MeetingRoom.is_active == is_active)
    
    if location_id:
        query = query.where(MeetingRoom.location_id == UUID(location_id))
    
    if capacity_min:
        query = query.where(MeetingRoom.capacity >= capacity_min)
    
    query = query.offset(skip).limit(limit).order_by(MeetingRoom.name)
    result = await db.execute(query)
    rooms = result.scalars().all()
    
    return {"rooms": [r.model_dump() for r in rooms]}


@router.get("/rooms/available")
async def get_available_rooms(
    location_id: Optional[str] = None,
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    capacity_needed: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get available rooms for a time slot."""
    # Get rooms that don't have conflicting bookings
    query = select(MeetingRoom).where(
        and_(
            MeetingRoom.tenant_id == user.tenant_id,
            MeetingRoom.is_active == True,
            ~MeetingRoom.id.in_(
                select(RoomBooking.room_id).where(
                    and_(
                        RoomBooking.tenant_id == user.tenant_id,
                        RoomBooking.status != BookingStatus.CANCELLED,
                        or_(
                            and_(
                                RoomBooking.start_time <= start_time,
                                RoomBooking.end_time > start_time,
                            ),
                            and_(
                                RoomBooking.start_time < end_time,
                                RoomBooking.end_time >= end_time,
                            ),
                            and_(
                                RoomBooking.start_time >= start_time,
                                RoomBooking.end_time <= end_time,
                            ),
                        ),
                    )
                )
            ),
        )
    )
    
    if location_id:
        query = query.where(MeetingRoom.location_id == UUID(location_id))
    
    if capacity_needed:
        query = query.where(MeetingRoom.capacity >= capacity_needed)
    
    result = await db.execute(query)
    rooms = result.scalars().all()
    
    return {"rooms": [r.model_dump() for r in rooms]}


@router.post("/rooms")
async def create_room(
    location_id: str,
    name: str,
    description: Optional[str] = None,
    floor: Optional[str] = None,
    capacity: int = 4,
    amenities: Optional[List[str]] = None,
    hourly_rate: float = 0.0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new meeting room."""
    room = MeetingRoom(
        tenant_id=user.tenant_id,
        location_id=UUID(location_id),
        name=name,
        description=description,
        floor=floor,
        capacity=capacity,
        amenities=amenities,
        hourly_rate=hourly_rate,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    
    return {"room": room.model_dump(), "message": "Meeting room created"}


# ============== ROOM BOOKINGS ==============

@router.get("/bookings/rooms")
async def list_room_bookings(
    room_id: Optional[str] = None,
    status: Optional[BookingStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List room bookings."""
    query = select(RoomBooking).where(RoomBooking.tenant_id == user.tenant_id)
    
    if room_id:
        query = query.where(RoomBooking.room_id == UUID(room_id))
    
    if status:
        query = query.where(RoomBooking.status == status)
    
    if start_date:
        query = query.where(RoomBooking.start_time >= start_date)
    
    if end_date:
        query = query.where(RoomBooking.end_time <= end_date)
    
    query = query.offset(skip).limit(limit).order_by(RoomBooking.start_time.desc())
    result = await db.execute(query)
    bookings = result.scalars().all()
    
    return {"bookings": [b.model_dump() for b in bookings]}


@router.post("/bookings/rooms")
async def create_room_booking(
    room_id: str,
    title: str,
    start_time: datetime,
    end_time: datetime,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Book a meeting room."""
    # Verify room exists and is available
    room = await db.get(MeetingRoom, UUID(room_id))
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check for conflicts
    conflict = await db.execute(
        select(RoomBooking).where(
            and_(
                RoomBooking.room_id == UUID(room_id),
                RoomBooking.tenant_id == user.tenant_id,
                RoomBooking.status != BookingStatus.CANCELLED,
                or_(
                    and_(
                        RoomBooking.start_time <= start_time,
                        RoomBooking.end_time > start_time,
                    ),
                    and_(
                        RoomBooking.start_time < end_time,
                        RoomBooking.end_time >= end_time,
                    ),
                ),
            )
        )
    )
    if conflict.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Room is not available for this time slot")
    
    booking = RoomBooking(
        tenant_id=user.tenant_id,
        room_id=UUID(room_id),
        booked_by_id=user.id,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        attendees=attendees,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    
    return {"booking": booking.model_dump(), "message": "Room booked successfully"}


# ============== CUSTOMERS ==============

@router.get("/customers")
async def list_customers(
    search: Optional[str] = None,
    customer_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all customers/clients."""
    query = select(Customer).where(Customer.tenant_id == user.tenant_id)
    
    if is_active is not None:
        query = query.where(Customer.is_active == is_active)
    
    if customer_type:
        query = query.where(Customer.customer_type == customer_type)
    
    if search:
        query = query.where(
            or_(
                Customer.company_name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%"),
            )
        )
    
    query = query.offset(skip).limit(limit).order_by(Customer.company_name)
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return {"customers": [c.model_dump() for c in customers]}


@router.post("/customers")
async def create_customer(
    company_name: str,
    contact_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    customer_type: str = "prospect",
    address: Optional[str] = None,
    industry: Optional[str] = None,
    source: Optional[str] = None,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new customer."""
    # Generate customer number using MAX to handle deletions properly
    max_result = await db.execute(
        select(func.max(Customer.customer_number)).where(Customer.tenant_id == user.tenant_id)
    )
    max_number = max_result.scalar()

    if max_number:
        # Extract number from CUST-XXXXXX format and increment
        try:
            current_num = int(max_number.replace("CUST-", ""))
            next_num = current_num + 1
        except (ValueError, AttributeError):
            next_num = 1
    else:
        next_num = 1

    customer_number = f"CUST-{next_num:06d}"

    customer = Customer(
        tenant_id=user.tenant_id,
        customer_number=customer_number,
        company_name=company_name,
        contact_name=contact_name,
        email=email,
        phone=phone,
        customer_type=customer_type,
        address=address,
        industry=industry,
        source=source,
        notes=notes,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return {"customer": customer.model_dump(), "message": "Customer created successfully"}


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a customer."""
    customer = await db.get(Customer, UUID(customer_id))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(customer)
    await db.commit()

    return {"message": "Customer deleted successfully"}


@router.put("/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    company_name: Optional[str] = None,
    contact_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    customer_type: Optional[str] = None,
    address: Optional[str] = None,
    industry: Optional[str] = None,
    source: Optional[str] = None,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update an existing customer."""
    customer = await db.get(Customer, UUID(customer_id))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if company_name is not None:
        customer.company_name = company_name
    if contact_name is not None:
        customer.contact_name = contact_name
    if email is not None:
        customer.email = email
    if phone is not None:
        customer.phone = phone
    if customer_type is not None:
        customer.customer_type = customer_type
    if address is not None:
        customer.address = address
    if industry is not None:
        customer.industry = industry
    if source is not None:
        customer.source = source
    if notes is not None:
        customer.notes = notes

    await db.commit()
    await db.refresh(customer)

    return {"customer": customer.model_dump(), "message": "Customer updated successfully"}


# ============== APPOINTMENTS ==============

@router.get("/appointments")
async def list_appointments(
    customer_id: Optional[str] = None,
    assigned_to_id: Optional[str] = None,
    status: Optional[AppointmentStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List appointments."""
    from sqlalchemy.orm import selectinload
    
    query = select(Appointment).where(Appointment.tenant_id == user.tenant_id)
    
    if customer_id:
        query = query.where(Appointment.customer_id == UUID(customer_id))

    if assigned_to_id:
        query = query.where(Appointment.assigned_to_id == UUID(assigned_to_id))
    
    if status:
        query = query.where(Appointment.status == status)
    
    if start_date:
        query = query.where(Appointment.start_time >= start_date)
    
    if end_date:
        query = query.where(Appointment.start_time <= end_date)
    
    # Eager load customer and assigned_to relationships
    query = query.options(selectinload(Appointment.customer), selectinload(Appointment.assigned_to))
    query = query.offset(skip).limit(limit).order_by(Appointment.start_time.desc())
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    # Convert to dict with relationships
    appointments_data = []
    for apt in appointments:
        apt_dict = {
            "id": str(apt.id),
            "tenant_id": str(apt.tenant_id),
            "customer_id": str(apt.customer_id) if apt.customer_id else None,
            "assigned_to_id": str(apt.assigned_to_id),
            "title": apt.title,
            "description": apt.description,
            "location": apt.location,
            "start_time": apt.start_time.isoformat() if apt.start_time else None,
            "end_time": apt.end_time.isoformat() if apt.end_time else None,
            "status": apt.status.value if apt.status else "scheduled",
            "appointment_type": apt.appointment_type,
            "outcome": apt.outcome,
            "next_steps": apt.next_steps,
            "reminder_sent": apt.reminder_sent,
            "created_at": apt.created_at.isoformat() if apt.created_at else None,
            "updated_at": apt.updated_at.isoformat() if apt.updated_at else None,
        }
        # Include customer relationship if loaded
        if apt.customer:
            apt_dict["customer"] = {
                "id": str(apt.customer.id),
                "company_name": apt.customer.company_name,
                "contact_name": apt.customer.contact_name,
                "email": apt.customer.email,
                "phone": apt.customer.phone,
            }
        # Include assigned_to (user) info
        if apt.assigned_to:
            apt_dict["employee"] = {
                "id": str(apt.assigned_to.id),
                "email": apt.assigned_to.email,
                "full_name": apt.assigned_to.full_name,
            }
        appointments_data.append(apt_dict)
    
    return {"appointments": appointments_data}


@router.post("/appointments")
async def create_appointment(
    customer_id: Optional[str] = Form(None),
    title: str = Form(...),
    start_time: str = Form(...),  # Receive as string, parse manually
    end_time: str = Form(...),    # Receive as string, parse manually
    assigned_to_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    appointment_type: str = Form("meeting"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new appointment."""
    from datetime import datetime, timezone
    
    # Parse datetime strings manually - strip timezone to make naive (database expects naive)
    try:
        start_dt = datetime.fromisoformat(start_time.replace("T", " ") if "T" in start_time else start_time)
        end_dt = datetime.fromisoformat(end_time.replace("T", " ") if "T" in end_time else end_time)
        
        # Remove timezone info if present (database uses TIMESTAMP WITHOUT TIME ZONE)
        if start_dt.tzinfo is not None:
            start_dt = start_dt.replace(tzinfo=None)
        if end_dt.tzinfo is not None:
            end_dt = end_dt.replace(tzinfo=None)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid datetime format: {e}")
    
    appointment = Appointment(
        tenant_id=user.tenant_id,
        customer_id=UUID(customer_id) if customer_id else None,
        assigned_to_id=UUID(assigned_to_id) if assigned_to_id else user.id,  # Default to current user
        title=title,
        description=description,
        location=location,
        start_time=start_dt,
        end_time=end_dt,
        appointment_type=appointment_type,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    
    return {"appointment": appointment.model_dump(), "message": "Appointment scheduled"}


# Note: Projects, Tasks, and Documents are managed via their dedicated modules

# ============== TIME ENTRIES ==============

@router.get("/time-entries")
async def list_time_entries(
    employee_id: Optional[str] = None,
    task_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    approved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List time entries."""
    query = select(TimeEntry).where(TimeEntry.tenant_id == user.tenant_id)
    
    if employee_id:
        query = query.where(TimeEntry.employee_id == UUID(employee_id))

    if task_id:
        query = query.where(TimeEntry.task_id == UUID(task_id))
    
    if start_date:
        query = query.where(TimeEntry.date >= start_date)
    
    if end_date:
        query = query.where(TimeEntry.date <= end_date)
    
    if approved is not None:
        query = query.where(TimeEntry.approved == approved)
    
    query = query.offset(skip).limit(limit).order_by(TimeEntry.date.desc(), TimeEntry.created_at.desc())
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return {"time_entries": [e.model_dump() for e in entries]}


@router.post("/time-entries")
async def create_time_entry(
    employee_id: str,
    date: datetime,
    hours: float,
    description: Optional[str] = None,
    task_id: Optional[str] = None,
    project_id: Optional[str] = None,
    billable: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a time entry."""
    entry = TimeEntry(
        tenant_id=user.tenant_id,
        employee_id=UUID(employee_id),
        date=date,
        hours=hours,
        description=description,
        task_id=UUID(task_id) if task_id else None,
        project_id=UUID(project_id) if project_id else None,
        billable=billable,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    return {"time_entry": entry.model_dump(), "message": "Time entry created"}


# ============== ATTENDANCE ==============

@router.get("/attendance")
async def list_attendance(
    employee_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List attendance records."""
    query = select(Attendance).where(Attendance.tenant_id == user.tenant_id)
    
    if employee_id:
        query = query.where(Attendance.employee_id == UUID(employee_id))
    
    if start_date:
        query = query.where(Attendance.date >= start_date)
    
    if end_date:
        query = query.where(Attendance.date <= end_date)
    
    query = query.offset(skip).limit(limit).order_by(Attendance.date.desc(), Attendance.check_in.desc())
    result = await db.execute(query)
    records = result.scalars().all()
    
    return {"attendance": [a.model_dump() for a in records]}


@router.post("/attendance/check-in")
async def check_in(
    employee_id: str,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record employee check-in."""
    now = datetime.utcnow()
    
    # Check if already checked in today
    existing = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == UUID(employee_id),
                Attendance.date >= now.replace(hour=0, minute=0, second=0),
                Attendance.check_out.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Employee already checked in today")
    
    attendance = Attendance(
        tenant_id=user.tenant_id,
        employee_id=UUID(employee_id),
        date=now,
        check_in=now,
        location=location,
        notes=notes,
    )
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)
    
    return {"attendance": attendance.model_dump(), "message": "Checked in successfully"}


@router.post("/attendance/check-out/{attendance_id}")
async def check_out(
    attendance_id: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record employee check-out."""
    attendance = await db.get(Attendance, UUID(attendance_id))
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    if attendance.check_out:
        raise HTTPException(status_code=400, detail="Already checked out")
    
    now = datetime.utcnow()
    attendance.check_out = now
    
    # Calculate hours worked
    if attendance.check_in:
        delta = now - attendance.check_in
        attendance.hours_worked = round(delta.total_seconds() / 3600, 2)
    
    if notes:
        attendance.notes = notes
    
    await db.commit()
    await db.refresh(attendance)
    
    return {"attendance": attendance.model_dump(), "message": "Checked out successfully"}


# ============== NOTES ==============

# Import the proper Note model from app.models
from app.models.note import Note as DbNote

@router.get("/notes")
async def list_notes(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List notes for the tenant using database storage."""
    from sqlalchemy import or_
    
    query = select(DbNote).where(DbNote.tenant_id == user.tenant_id)
    
    if search:
        query = query.where(
            or_(
                DbNote.title.ilike(f"%{search}%"),
                DbNote.content.ilike(f"%{search}%"),
            )
        )
    
    query = query.offset(skip).limit(limit).order_by(DbNote.updated_at.desc())
    result = await db.execute(query)
    notes = result.scalars().all()
    
    return {"notes": [n.to_dict() for n in notes]}


@router.post("/notes")
async def create_note(
    title: str = Form(...),
    content: str = Form(...),
    is_pinned: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new note in the database."""
    note = DbNote(
        tenant_id=user.tenant_id,
        title=title,
        content=content,
        source_type="manual",
        created_by_id=user.id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    return {"note": note.to_dict(), "message": "Note created successfully"}


@router.put("/notes/{note_id}")
async def update_note(
    note_id: str,
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    is_pinned: Optional[bool] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a note in the database."""
    note = await db.get(DbNote, UUID(note_id))
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
    # Note: The database Note model doesn't have is_pinned, skipping that field
    
    await db.commit()
    await db.refresh(note)
    
    return {"note": note.to_dict(), "message": "Note updated successfully"}


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a note from the database."""
    note = await db.get(DbNote, UUID(note_id))
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.delete(note)
    await db.commit()
    
    return {"message": "Note deleted successfully"}


# ============== DASHBOARD STATS ==============

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dashboard statistics."""
    tenant_id = user.tenant_id
    
    # Count employees
    employees_count = await db.execute(
        select(func.count(Employee.id)).where(
            and_(Employee.tenant_id == tenant_id, Employee.is_active == True)
        )
    )
    
    # Count customers
    customers_count = await db.execute(
        select(func.count(Customer.id)).where(
            and_(Customer.tenant_id == tenant_id, Customer.is_active == True)
        )
    )
    
    # Count today's appointments
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today.replace(hour=23, minute=59, second=59)
    appointments_today = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.tenant_id == tenant_id,
                Appointment.start_time >= today,
                Appointment.start_time <= tomorrow,
                Appointment.status == AppointmentStatus.SCHEDULED,
            )
        )
    )
    
    # Today's room bookings
    bookings_today = await db.execute(
        select(func.count(RoomBooking.id)).where(
            and_(
                RoomBooking.tenant_id == tenant_id,
                RoomBooking.start_time >= today,
                RoomBooking.start_time <= tomorrow,
                RoomBooking.status != BookingStatus.CANCELLED,
            )
        )
    )
    
    return {
        "total_employees": employees_count.scalar() or 0,
        "total_customers": customers_count.scalar() or 0,
        "active_appointments": appointments_today.scalar() or 0,
        "room_bookings_today": bookings_today.scalar() or 0,
    }
