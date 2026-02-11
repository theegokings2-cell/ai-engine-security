"""
Customer Portal Authentication
Self-service customer registration and login.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import bcrypt
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, field_validator

from app.db.session import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.user import User, UserRole

router = APIRouter(prefix="/portal/auth", tags=["Portal Auth"])

# Password hashing (using bcrypt directly - passlib has compatibility issues)

# OAuth2 scheme for portal
oauth2_scheme_portal = OAuth2PasswordBearer(tokenUrl="/portal/auth/login", auto_error=False)


def validate_password_strength(password: str) -> str:
    """Validate password meets minimum security requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    return password


class CustomerRegisterRequest(BaseModel):
    """Customer registration request."""
    email: EmailStr
    full_name: str
    password: str
    company_name: Optional[str] = None  # Optional organization name

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class CustomerRegisterResponse(BaseModel):
    """Customer registration response."""
    user: dict
    message: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


@router.post("/register", response_model=CustomerRegisterResponse)
async def register_customer(
    request: CustomerRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new customer.
    
    - If company_name provided: links to existing organization or creates new one
    - If no company_name: creates a personal organization for the customer
    """
    import bcrypt
    
    email = request.email
    full_name = request.full_name
    password = request.password
    company_name = request.company_name
    
    # Check if user with email already exists
    existing_user = await db.execute(
        select(User).where(User.email == email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists"
        )
    
    # Get or create organization
    # For now, create a personal organization for the customer
    from app.models.office.office_models import Organization
    from sqlalchemy import func
    
    if company_name:
        # Try to find existing organization
        org_result = await db.execute(
            select(Organization).where(Organization.name.ilike(company_name))
        )
        organization = org_result.scalar_one_or_none()
        
        if not organization:
            # Create new organization
            org_id = uuid4()
            organization = Organization(
                id=org_id,
                name=company_name,
                slug=company_name.lower().replace(" ", "-"),
            )
            db.add(organization)
            await db.flush()
    else:
        # Create personal organization for customer
        org_id = uuid4()
        organization = Organization(
            id=org_id,
            name=f"{full_name}'s Workspace",
            slug=f"personal-{uuid4().hex[:8]}",
        )
        db.add(organization)
        await db.flush()
    
    # Hash password with bcrypt directly
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create user with CUSTOMER role
    user = User(
        id=uuid4(),
        tenant_id=organization.id,
        email=email,
        hashed_password=hashed_pw,
        full_name=full_name,
        role=UserRole.CUSTOMER.value,
        is_active=True,
        is_verified=True,  # Auto-verify portal customers
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Auto-login after registration - generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "tenant_id": str(user.tenant_id)},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organization": organization.name,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "message": "Customer account created successfully"
    }


@router.post("/login", response_model=TokenResponse)
async def login_customer(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate customer and return access token.
    """
    import bcrypt
    
    # Find user by email
    result = await db.execute(
        select(User).where(
            and_(
                User.email == form_data.username,
                User.role == UserRole.CUSTOMER.value
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not bcrypt.checkpw(
        form_data.password.encode('utf-8'),
        user.hashed_password.encode('utf-8')
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "tenant_id": str(user.tenant_id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/employee-login", response_model=TokenResponse)
async def login_employee(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate employee and return access token for portal access.
    Allows employees to access the employee portal.
    """
    import bcrypt
    
    # Find user by email (employees use email, not username)
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is an employee or manager
    if user.role not in [UserRole.EMPLOYEE.value, UserRole.MANAGER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This portal is for employees only"
        )
    
    # Verify password
    if not bcrypt.checkpw(
        form_data.password.encode('utf-8'),
        user.hashed_password.encode('utf-8')
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id), 
            "role": user.role, 
            "tenant_id": str(user.tenant_id),
            "portal_type": "employee"
        },
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh_token,
    }


async def get_current_employee(
    token: str = Depends(oauth2_scheme_portal),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated employee from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        portal_type: str = payload.get("portal_type")

        if user_id is None or portal_type != "employee":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    return user


@router.get("/employee-me")
async def get_employee_profile(
    current_user: User = Depends(get_current_employee),
):
    """Get current employee profile with permissions."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "permissions": current_user.get_all_permissions(),
        "phone": current_user.phone,
        "notification_preference": current_user.notification_preference,
        "timezone": current_user.timezone,
    }


async def get_current_portal_user(
    token: str = Depends(oauth2_scheme_portal),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated customer."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        
        if user_id is None or role != UserRole.CUSTOMER.value:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    return user


@router.get("/me")
async def get_current_customer(
    current_user: User = Depends(get_current_portal_user),
):
    """Get current customer profile with permissions."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "permissions": current_user.get_all_permissions(),
        "phone": current_user.phone,
        "notification_preference": current_user.notification_preference,
        "timezone": current_user.timezone,
    }


@router.post("/logout")
async def logout_customer():
    """Logout customer (client-side token removal)."""
    return {"message": "Successfully logged out"}


# ============== PASSWORD RESET ==============

class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class PasswordChange(BaseModel):
    """Password change request (requires auth)."""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


@router.post("/password-reset/request")
@limiter.limit("3/minute;10/hour")
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email.
    In production, send an email with reset link.
    """
    from sqlalchemy import text

    # Find user by email
    result = await db.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Don't reveal whether email exists
        return {"message": "If an account exists, a password reset email has been sent"}
    
    # Generate reset token (in production, send via email)
    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "password_reset"},
        expires_delta=timedelta(hours=1)
    )
    
    # Store reset token (in production, use a dedicated table with expiry)
    try:
        await db.execute(
            text("UPDATE users SET reset_token = :token WHERE id = :user_id"),
            {"token": reset_token, "user_id": user.id}
        )
        await db.commit()
    except Exception:
        # Table might not have reset_token column - log and continue
        pass
    
    # TODO: In production, send email with reset link containing the token
    return {
        "message": "If an account exists, a password reset email has been sent",
    }


@router.post("/password-reset/confirm")
@limiter.limit("5/minute;20/hour")
async def confirm_password_reset(
    request: Request,
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm password reset with token.
    """
    from sqlalchemy import text

    try:
        payload = jwt.decode(body.token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid reset token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid reset token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Hash new password
    hashed_pw = bcrypt.hashpw(body.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update password and clear reset token
    try:
        await db.execute(
            text("UPDATE users SET hashed_password = :password, reset_token = NULL WHERE id = :user_id"),
            {"password": hashed_pw, "user_id": user_id}
        )
        await db.commit()
    except Exception:
        # Table might not have reset_token column
        await db.execute(
            text("UPDATE users SET hashed_password = :password WHERE id = :user_id"),
            {"password": hashed_pw, "user_id": user_id}
        )
        await db.commit()
    
    return {"message": "Password has been reset successfully"}


@router.post("/password-change")
async def change_password(
    request: PasswordChange,
    current_user: User = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password for authenticated user.
    """
    from sqlalchemy import text
    
    # Verify current password
    if not bcrypt.checkpw(
        request.current_password.encode('utf-8'),
        current_user.hashed_password.encode('utf-8')
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    hashed_pw = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update password
    await db.execute(
        text("UPDATE users SET hashed_password = :password WHERE id = :user_id"),
        {"password": hashed_pw, "user_id": current_user.id}
    )
    await db.commit()
    
    return {"message": "Password has been changed successfully"}
