"""
Full diagnostic check for Office Manager API
"""
import sys
sys.path.insert(0, '.')

async def full_diagnostic():
    print("=" * 60)
    print("OFFICE MANAGER API - FULL DIAGNOSTIC")
    print("=" * 60)
    
    errors = []
    
    # 1. Check imports
    print("\n[1/8] Checking imports...")
    try:
        from app.db.session import engine, async_session_factory, init_db
        print("  ✓ Database session imports OK")
    except Exception as e:
        errors.append(f"DB session import: {e}")
        print(f"  ✗ DB session import: {e}")
    
    try:
        from app.models.user import User
        from app.models.tenant import Tenant
        from app.models.role import Role
        from app.models.audit_log import AuditLog
        print("  ✓ Model imports OK")
    except Exception as e:
        errors.append(f"Model imports: {e}")
        print(f"  ✗ Model imports: {e}")
    
    try:
        from app.core.security import get_password_hash, verify_password, create_access_token
        print("  ✓ Security imports OK")
    except Exception as e:
        errors.append(f"Security imports: {e}")
        print(f"  ✗ Security imports: {e}")
    
    try:
        from app.api.v1.auth import router
        print("  ✓ Auth router imports OK")
    except Exception as e:
        errors.append(f"Auth router: {e}")
        print(f"  ✗ Auth router: {e}")
    
    # 2. Check database connection
    print("\n[2/8] Checking database connection...")
    try:
        from sqlalchemy import text
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            print("  ✓ Database connection OK")
    except Exception as e:
        errors.append(f"DB connection: {e}")
        print(f"  ✗ DB connection: {e}")
    
    # 3. Check tables exist
    print("\n[3/8] Checking tables...")
    try:
        from sqlalchemy import text
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"  Tables found: {tables}")
            expected = ['users', 'tenants', 'roles', 'audit_logs', 'events', 'tasks', 'notes']
            missing = [t for t in expected if t not in tables]
            if missing:
                errors.append(f"Missing tables: {missing}")
                print(f"  ✗ Missing tables: {missing}")
            else:
                print("  ✓ All expected tables exist")
    except Exception as e:
        errors.append(f"Tables check: {e}")
        print(f"  ✗ Tables check: {e}")
    
    # 4. Check if user exists
    print("\n[4/8] Checking for existing users...")
    try:
        from sqlalchemy import text
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"  Users in database: {user_count}")
            if user_count == 0:
                print("  ⚠ No users - register will be needed")
            else:
                result = await session.execute(text("SELECT email, role FROM users LIMIT 5"))
                users = result.fetchall()
                for u in users:
                    print(f"    - {u[0]} ({u[1]})")
    except Exception as e:
        errors.append(f"User check: {e}")
        print(f"  ✗ User check: {e}")
    
    # 5. Test password hashing
    print("\n[5/8] Testing password hashing...")
    try:
        from app.core.security import get_password_hash, verify_password
        test_pass = "password123"
        hashed = get_password_hash(test_pass)
        print(f"  Hash generated: {hashed[:20]}...")
        verified = verify_password(test_pass, hashed)
        if verified:
            print("  ✓ Password hashing/verification OK")
        else:
            errors.append("Password verification failed")
            print("  ✗ Password verification failed")
    except Exception as e:
        errors.append(f"Password hash: {e}")
        print(f"  ✗ Password hash: {e}")
    
    # 6. Test JWT token creation
    print("\n[6/8] Testing JWT token creation...")
    try:
        from app.core.security import create_access_token
        from datetime import timedelta
        token = create_access_token(
            data={"sub": "test-user-id", "tenant_id": "test-tenant-id", "role": "admin"},
            expires_delta=timedelta(minutes=30)
        )
        print(f"  Token created: {token[:30]}...")
        print("  ✓ JWT token creation OK")
    except Exception as e:
        errors.append(f"JWT creation: {e}")
        print(f"  ✗ JWT creation: {e}")
    
    # 7. Check auth endpoints schema
    print("\n[7/8] Checking auth endpoint schemas...")
    try:
        from app.models.user import UserCreate
        # Test UserCreate validation
        user_data = UserCreate(
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        print(f"  UserCreate schema valid: email={user_data.email}")
        print("  ✓ Auth schemas OK")
    except Exception as e:
        errors.append(f"Auth schema: {e}")
        print(f"  ✗ Auth schema: {e}")
    
    # 8. Test actual register (dry run check)
    print("\n[8/8] Testing register flow (simulated)...")
    try:
        from app.core.security import get_password_hash
        from app.models.tenant import Tenant
        from uuid import uuid4
        
        # Simulate what register does
        email = "test_register@example.com"
        tenant = Tenant(
            id=uuid4(),
            name="Test Company",
            slug=email.split("@")[0].lower().replace(".", "-"),
            settings={},
            subscription_tier="pro",
        )
        print(f"  Tenant object created: {tenant.name}")
        
        hashed_pw = get_password_hash("testpassword123")
        print(f"  Password hashed successfully")
        print("  ✓ Register flow simulation OK")
    except Exception as e:
        errors.append(f"Register simulation: {e}")
        print(f"  ✗ Register simulation: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"DIAGNOSTIC FAILED - {len(errors)} error(s) found:")
        for i, e in enumerate(errors, 1):
            print(f"  {i}. {e}")
    else:
        print("ALL CHECKS PASSED ✓")
        print("\nReady for tomorrow:")
        print("  1. Start server: python -B -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("  2. Register: POST /api/v1/auth/register")
        print("  3. Login: POST /api/v1/auth/login")
    print("=" * 60)
    
    return len(errors) == 0

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(full_diagnostic())
    sys.exit(0 if success else 1)
