"""
Customer Portal Authentication
Secure customer-facing authentication with JWT tokens
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import settings
from app.models.portal import CustomerUser, CustomerSession
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/portal/auth", tags=["Customer Portal Auth"])

# OAuth2 scheme for customers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/portal/auth/login")


# ============ Pydantic Schemas ============

class CustomerUserCreate(BaseModel):
    """Schema for creating customer portal user"""
    email: EmailStr
    password: str
    customer_id: str
    first_name: str
    last_name: str
    phone: Optional[str] = None


class SelfRegisterRequest(BaseModel):
    """Schema for self-registration"""
    email: EmailStr
    password: str
    full_name: str
    company_name: Optional[str] = None


class CustomerUserResponse(BaseModel):
    """Schema for customer user response"""
    id: UUID
    customer_id: UUID
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    customer_user: CustomerUserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# ============ Password Utilities ============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash using bcrypt directly"""
    import bcrypt
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt directly"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(customer_user_id: str, customer_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": customer_user_id,
        "customer_id": customer_id,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(customer_user_id: str, customer_id: str) -> str:
    """Create JWT refresh token (longer expiry)"""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": customer_user_id,
        "customer_id": customer_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


# ============ Dependency ============

async def get_current_customer_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> CustomerUser:
    """Get current authenticated customer user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "access":
            raise credentials_exception
        
        customer_user_id: str = payload.get("sub")
        customer_id: str = payload.get("customer_id")
        
        if customer_user_id is None or customer_id is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    # Get customer user from database
    result = await db.execute(
        select(CustomerUser).where(
            and_(
                CustomerUser.id == customer_user_id,
                CustomerUser.customer_id == customer_id,
                CustomerUser.is_active == True
            )
        )
    )
    
    customer_user = result.scalar_one_or_none()
    
    if customer_user is None:
        raise credentials_exception
    
    return customer_user


# ============ Endpoints ============

@router.post("/register", response_model=CustomerUserResponse)
async def register_customer_user(
    user_data: CustomerUserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new customer portal user
    
    This is typically called by internal staff when setting up
    customer access, not by self-registration.
    """
    # Check if email already exists
    result = await db.execute(
        select(CustomerUser).where(CustomerUser.email == user_data.email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create customer user
    customer_user = CustomerUser(
        customer_id=user_data.customer_id,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
    )
    
    db.add(customer_user)
    await db.commit()
    await db.refresh(customer_user)
    
    logger.info(
        "customer_user_created",
        customer_user_id=str(customer_user.id),
        customer_id=customer_user.customer_id,
        email=customer_user.email
    )
    
    return customer_user


# Self-registration endpoint (simpler, for public signup)
@router.post("/self-register")
async def self_register_customer(
    request: SelfRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Self-registration for customers (no customer_id required).
    Creates a new customer and customer user in one step.
    """
    from app.models.office.office_models import Customer
    from app.models.tenant import Tenant
    from uuid import uuid4
    
    email = request.email
    password = request.password
    full_name = request.full_name
    company_name = request.company_name or f"{full_name}'s Company"
    
    # Check if user with email already exists
    result = await db.execute(
        select(CustomerUser).where(CustomerUser.email == email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Parse full name
    name_parts = full_name.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    # Get or create a default tenant for self-registered users
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.name == "Self-Registered Customers")
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        tenant = Tenant(
            id=uuid4(),
            name="Self-Registered Customers",
            slug="self-registered",
            subscription_tier="free",
        )
        db.add(tenant)
        await db.flush()
    
    # Create a customer for this user
    customer = Customer(
        id=uuid4(),
        tenant_id=tenant.id,
        customer_number=f"SR-{uuid4().hex[:8].upper()}",
        company_name=company_name,
        contact_name=full_name,
        email=email,
    )
    db.add(customer)
    await db.flush()
    
    # Create customer user linked to the customer
    customer_user = CustomerUser(
        customer_id=customer.id,
        email=email,
        hashed_password=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        phone=None,
    )
    
    db.add(customer_user)
    await db.commit()
    await db.refresh(customer_user)
    
    logger.info(
        "customer_self_registered",
        customer_user_id=str(customer_user.id),
        email=email
    )
    
    return {
        "message": "Registration successful",
        "user": {
            "id": str(customer_user.id),
            "email": customer_user.email,
            "first_name": customer_user.first_name,
            "last_name": customer_user.last_name,
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login_customer(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Customer portal login
    Returns JWT access and refresh tokens
    """
    # Find customer user by email
    result = await db.execute(
        select(CustomerUser).where(
            and_(
                CustomerUser.email == form_data.username,
                CustomerUser.is_active == True
            )
        )
    )
    
    customer_user = result.scalar_one_or_none()
    
    if not customer_user or not verify_password(form_data.password, customer_user.hashed_password):
        logger.warning(
            "customer_login_failed",
            email=form_data.username,
            reason="Invalid credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(
        str(customer_user.id),
        str(customer_user.customer_id)
    )
    refresh_token = create_refresh_token(
        str(customer_user.id),
        str(customer_user.customer_id)
    )
    
    # Create session record
    session = CustomerSession(
        customer_user_id=customer_user.id,
        customer_id=customer_user.customer_id,
        token=access_token,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    db.add(session)
    await db.commit()
    
    logger.info(
        "customer_login_success",
        customer_user_id=str(customer_user.id),
        customer_id=customer_user.customer_id
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        customer_user=CustomerUserResponse.model_validate(customer_user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        customer_user_id: str = payload.get("sub")
        customer_id: str = payload.get("customer_id")
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get customer user
    result = await db.execute(
        select(CustomerUser).where(
            and_(
                CustomerUser.id == customer_user_id,
                CustomerUser.customer_id == customer_id,
                CustomerUser.is_active == True
            )
        )
    )
    
    customer_user = result.scalar_one_or_none()
    
    if not customer_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token = create_access_token(customer_user_id, customer_id)
    refresh_token = create_refresh_token(customer_user_id, customer_id)
    
    logger.info(
        "customer_token_refreshed",
        customer_user_id=customer_user_id,
        customer_id=customer_id
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        customer_user=CustomerUserResponse.model_validate(customer_user)
    )


@router.post("/logout")
async def logout_customer(
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout customer user (invalidate session)
    """
    # Invalidate all sessions for this user
    result = await db.execute(
        select(CustomerSession).where(
            and_(
                CustomerSession.customer_user_id == current_user.id,
                CustomerSession.is_active == True
            )
        )
    )
    
    sessions = result.scalars().all()
    for session in sessions:
        session.is_active = False
        session.revoked_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(
        "customer_logout",
        customer_user_id=str(current_user.id),
        customer_id=current_user.customer_id
    )
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=CustomerUserResponse)
async def get_current_customer_info(
    current_user: CustomerUser = Depends(get_current_customer_user)
):
    """
    Get current customer user information
    """
    return current_user


@router.put("/password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: CustomerUser = Depends(get_current_customer_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change customer user password
    """
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.hashed_password = get_password_hash(new_password)
    await db.commit()
    
    logger.info(
        "customer_password_changed",
        customer_user_id=str(current_user.id)
    )
    
    return {"message": "Password changed successfully"}
