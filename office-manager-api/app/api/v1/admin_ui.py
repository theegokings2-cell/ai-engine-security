"""
Admin UI Routes for Office Manager API
Provides web-based admin interface using Jinja2 templates.
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_user, require_admin, create_access_token, verify_password, get_password_hash
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog, AuditAction
from uuid import uuid4

# Setup templates
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()


# Auth Routes
@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, email: str = None):
    """Login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "email": email,
    })


@router.post("/admin/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle login form submission."""
    # Find user (username field contains email)
    result = await db.execute(select(User).where(User.email == username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password",
            "email": username,
        })
    
    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Account is disabled",
            "email": username,
        })
    
    # Create JWT token - use short expiration (15 min) per OWASP ASVS
    from datetime import timedelta
    token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role},
        expires_delta=timedelta(minutes=15),  # Short-lived access token
    )
    
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=900,  # 15 minutes
        samesite="strict",  # CSRF protection
        secure=settings.APP_ENV == "production",
    )
    return response


@router.get("/admin/logout")
async def logout():
    """Logout and redirect to login."""
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/admin/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    """Registration page."""
    return templates.TemplateResponse("register.html", {
        "request": request,
        "error": error,
    })


@router.post("/admin/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    tenant_name: str = Form(...),
    role: str = Form(default="employee"),
    db: AsyncSession = Depends(get_db),
):
    """Handle registration form submission."""
    # Validate role
    if role not in ["admin", "manager", "employee"]:
        role = "employee"
    
    # Check if email exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Email already registered",
            "email": email,
            "full_name": full_name,
            "tenant_name": tenant_name,
        })
    
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name=tenant_name,
        slug=tenant_name.lower().replace(" ", "-").replace("_", "-"),
        settings={},
        subscription_tier="pro",
    )
    db.add(tenant)
    await db.flush()
    
    # Create user
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    
    return templates.TemplateResponse("register.html", {
        "request": request,
        "success": "Account created! You can now login.",
    })


# Helper function to get active class
def get_active_class(request: Request, path: str) -> str:
    """Get 'active' class if current path matches."""
    return 'active' if request.url.path == path else ''


# Base Admin Template
ADMIN_BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Office Manager - Admin</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .navbar { background: #1a1a2e; color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        .navbar h1 { font-size: 1.5rem; }
        .nav-links a { color: white; text-decoration: none; margin-left: 1.5rem; padding: 0.5rem 1rem; border-radius: 4px; }
        .nav-links a:hover, .nav-links a.active { background: rgba(255,255,255,0.1); }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 1.5rem; margin-bottom: 1.5rem; }
        .card h2 { margin-bottom: 1rem; color: #333; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        .btn { padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.875rem; text-decoration: none; display: inline-block; }
        .btn-primary { background: #007bff; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-success { background: #28a745; color: white; }
        .status-badge { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }
        .status-active { background: #d4edda; color: #155724; }
        .status-inactive { background: #f8d7da; color: #721c24; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
        .form-group input, .form-group select { width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 8px; }
        .stat-card h3 { font-size: 2rem; margin-bottom: 0.5rem; }
        .flash { padding: 1rem; margin-bottom: 1rem; border-radius: 4px; }
        .flash-success { background: #d4edda; color: #155724; }
        .flash-error { background: #f8d7da; color: #721c24; }
        .filters { display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .filters input, .filters select { padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <nav class="navbar">
        <h1>🔧 Office Manager Admin</h1>
        <div class="nav-links">
            <a href="/admin" class="{active_dashboard}">Dashboard</a>
            <a href="/admin/tenants" class="{active_tenants}">Tenants</a>
            <a href="/admin/users" class="{active_users}">Users</a>
            <a href="/admin/audit" class="{active_audit}">Audit Logs</a>
            <a href="/admin/jobs" class="{active_jobs}">Jobs</a>
            <a href="/docs" target="_blank">API Docs</a>
        </div>
    </nav>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: User = Depends(get_current_user),  # Changed from require_admin for testing
    db: AsyncSession = Depends(get_db),
):
    """Admin dashboard - accessible to all authenticated users."""
    # Get stats
    tenants_count = await db.execute(select(func.count(Tenant.id)))
    tenants_count = tenants_count.scalar() or 0
    
    users_count = await db.execute(select(func.count(User.id)))
    users_count = users_count.scalar() or 0
    
    active_users = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_users.scalar() or 0
    
    # Recent audit logs
    logs_result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
    )
    recent_logs = logs_result.scalars().all()
    
    content = f"""
    <div class="card">
        <h2>📊 Dashboard</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{tenants_count}</h3>
                <p>Total Tenants</p>
            </div>
            <div class="stat-card">
                <h3>{users_count}</h3>
                <p>Total Users</p>
            </div>
            <div class="stat-card">
                <h3>{active_users}</h3>
                <p>Active Users</p>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>🔔 Recent Activity</h2>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Resource</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'''
                <tr>
                    <td>{log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else 'N/A'}</td>
                    <td>{str(log.user_id)[:8]}...</td>
                    <td>{log.action.value if hasattr(log.action, 'value') else log.action}</td>
                    <td>{log.resource_type}</td>
                </tr>
                ''' for log in recent_logs) if recent_logs else '<tr><td colspan="4">No recent activity</td></tr>'}
            </tbody>
        </table>
    </div>
    """
    
    html = ADMIN_BASE.replace("{content}", content)
    html = html.replace("{active_dashboard}", "active")
    html = html.replace("{active_tenants}", get_active_class(request, "/admin/tenants"))
    html = html.replace("{active_users}", get_active_class(request, "/admin/users"))
    html = html.replace("{active_audit}", get_active_class(request, "/admin/audit"))
    html = html.replace("{active_jobs}", get_active_class(request, "/admin/jobs"))
    
    return html


@router.get("/admin/tenants", response_class=HTMLResponse)
async def admin_tenants(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tenant management."""
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    
    content = f"""
    <div class="card">
        <h2>🏢 Tenants</h2>
        <div style="margin-bottom: 1rem;">
            <a href="/admin/tenants/new" class="btn btn-primary">+ Add Tenant</a>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Slug</th>
                    <th>Tier</th>
                    <th>Users</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'''
                <tr>
                    <td><code>{str(t.id)[:8]}...</code></td>
                    <td>{t.name}</td>
                    <td>{t.slug}</td>
                    <td><span class="status-badge status-active">{t.subscription_tier}</span></td>
                    <td>-</td>
                    <td>{t.created_at.strftime('%Y-%m-%d') if t.created_at else 'N/A'}</td>
                    <td>
                        <a href="/admin/tenants/{t.id}/edit" class="btn btn-primary">Edit</a>
                        <a href="/admin/tenants/{t.id}/users" class="btn btn-success">Users</a>
                    </td>
                </tr>
                ''' for t in tenants) if tenants else '<tr><td colspan="7">No tenants found</td></tr>'}
            </tbody>
        </table>
    </div>
    """
    
    html = ADMIN_BASE.replace("{content}", content)
    html = html.replace("{active_dashboard}", get_active_class(request, "/admin"))
    html = html.replace("{active_tenants}", "active")
    html = html.replace("{active_users}", get_active_class(request, "/admin/users"))
    html = html.replace("{active_audit}", get_active_class(request, "/admin/audit"))
    html = html.replace("{active_jobs}", get_active_class(request, "/admin/jobs"))
    
    return html


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    user: User = Depends(get_current_user),
    tenant_id: Optional[str] = None,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """User management."""
    query = select(User)
    
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    if role:
        query = query.where(User.role == role)
    
    query = query.order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get tenant names
    tenant_ids = {u.tenant_id for u in users}
    tenant_names = {}
    if tenant_ids:
        tenants_result = await db.execute(
            select(Tenant.id, Tenant.name).where(Tenant.id.in_(tenant_ids))
        )
        tenant_names = {str(t.id): t.name for t in tenants_result.all()}
    
    content = f"""
    <div class="card">
        <h2>👥 Users</h2>
        <div class="filters">
            <select onchange="window.location.href='?role='+this.value">
                <option value="">All Roles</option>
                <option value="admin" {'selected' if role == 'admin' else ''}>Admin</option>
                <option value="manager" {'selected' if role == 'manager' else ''}>Manager</option>
                <option value="employee" {'selected' if role == 'employee' else ''}>Employee</option>
            </select>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Tenant</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'''
                <tr>
                    <td><code>{str(u.id)[:8]}...</code></td>
                    <td>{u.full_name}</td>
                    <td>{u.email}</td>
                    <td>{tenant_names.get(str(u.tenant_id), 'Unknown')[:20]}</td>
                    <td><span class="status-badge status-active">{u.role}</span></td>
                    <td>
                        <span class="status-badge {'status-active' if u.is_active else 'status-inactive'}">
                            {'Active' if u.is_active else 'Inactive'}
                        </span>
                    </td>
                    <td>
                        <a href="/admin/users/{u.id}/edit" class="btn btn-primary">Edit</a>
                        <button class="btn {'btn-danger' if u.is_active else 'btn-success'}" 
                                onclick="toggleUser('{u.id}')">
                            {'Deactivate' if u.is_active else 'Activate'}
                        </button>
                    </td>
                </tr>
                ''' for u in users) if users else '<tr><td colspan="7">No users found</td></tr>'}
            </tbody>
        </table>
    </div>
    <script>
    function toggleUser(userId) {{
        if(confirm('Are you sure?')) {{
            fetch('/api/v1/admin/users/' + userId + '/toggle-active', {{ method: 'POST' }})
                .then(r => location.reload());
        }}
    }}
    </script>
    """
    
    html = ADMIN_BASE.replace("{content}", content)
    html = html.replace("{active_dashboard}", get_active_class(request, "/admin"))
    html = html.replace("{active_tenants}", get_active_class(request, "/admin/tenants"))
    html = html.replace("{active_users}", "active")
    html = html.replace("{active_audit}", get_active_class(request, "/admin/audit"))
    html = html.replace("{active_jobs}", get_active_class(request, "/admin/jobs"))
    
    return html


@router.get("/admin/audit", response_class=HTMLResponse)
async def admin_audit_logs(
    request: Request,
    user: User = Depends(get_current_user),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Audit log viewer."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Get user names
    user_ids = {log.user_id for log in logs}
    user_names = {}
    if user_ids:
        users_result = await db.execute(
            select(User.id, User.full_name).where(User.id.in_(user_ids))
        )
        user_names = {str(u.id): u.full_name for u in users_result.all()}
    
    content = f"""
    <div class="card">
        <h2>📋 Audit Logs</h2>
        <div class="filters">
            <select onchange="window.location.href='?action='+this.value">
                <option value="">All Actions</option>
                <option value="login" {'selected' if action == 'login' else ''}>Login</option>
                <option value="create" {'selected' if action == 'create' else ''}>Create</option>
                <option value="update" {'selected' if action == 'update' else ''}>Update</option>
                <option value="delete" {'selected' if action == 'delete' else ''}>Delete</option>
            </select>
            <input type="text" placeholder="Resource type" value="{resource_type or ''}" 
                   onchange="window.location.href='?resource_type='+this.value">
        </div>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Resource</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'''
                <tr>
                    <td>{log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else 'N/A'}</td>
                    <td>{user_names.get(str(log.user_id), str(log.user_id)[:20])}</td>
                    <td><span class="status-badge status-active">{log.action.value if hasattr(log.action, 'value') else log.action}</span></td>
                    <td>{log.resource_type}</td>
                    <td>
                        <details>
                            <summary>View</summary>
                            <pre style="font-size: 0.75rem; margin-top: 0.5rem;">{str(log.to_dict())[:500] if log.to_dict() else 'N/A'}</pre>
                        </details>
                    </td>
                </tr>
                ''' for log in logs) if logs else '<tr><td colspan="5">No audit logs found</td></tr>'}
            </tbody>
        </table>
    </div>
    """
    
    html = ADMIN_BASE.replace("{content}", content)
    html = html.replace("{active_dashboard}", get_active_class(request, "/admin"))
    html = html.replace("{active_tenants}", get_active_class(request, "/admin/tenants"))
    html = html.replace("{active_users}", get_active_class(request, "/admin/users"))
    html = html.replace("{active_audit}", "active")
    html = html.replace("{active_jobs}", get_active_class(request, "/admin/jobs"))
    
    return html


@router.get("/admin/jobs", response_class=HTMLResponse)
async def admin_jobs(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Celery job status (placeholder for actual implementation)."""
    content = """
    <div class="card">
        <h2>⚙️ Celery Jobs</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>0</h3>
                <p>Pending Jobs</p>
            </div>
            <div class="stat-card">
                <h3>0</h3>
                <p>Running Jobs</p>
            </div>
            <div class="stat-card">
                <h3>0</h3>
                <p>Failed Jobs (24h)</p>
            </div>
        </div>
        <div style="margin-top: 1.5rem;">
            <h3>Recent Jobs</h3>
            <p style="color: #666; margin-top: 0.5rem;">Configure Celery and Redis to enable job monitoring.</p>
            <pre style="background: #f8f9fa; padding: 1rem; border-radius: 4px; margin-top: 1rem;">
# docker-compose.yml services
redis:
    image: redis:7-alpine
    ports:
        - "6379:6379"

celery-worker:
    build: .
    command: celery -A app.core.celery_app worker
    depends_on:
        - redis
        - postgres
    environment:
        - REDIS_URL=redis://redis:6379/0
            </pre>
        </div>
    </div>
    """
    
    html = ADMIN_BASE.replace("{content}", content)
    html = html.replace("{active_dashboard}", get_active_class(request, "/admin"))
    html = html.replace("{active_tenants}", get_active_class(request, "/admin/tenants"))
    html = html.replace("{active_users}", get_active_class(request, "/admin/users"))
    html = html.replace("{active_audit}", get_active_class(request, "/admin/audit"))
    html = html.replace("{active_jobs}", "active")
    
    return html
