import sys
sys.path.insert(0, 'C:/Users/antho/clawd/office-manager-api')

print('=== SETUP SCRIPT ===')

import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory, init_db
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import Role
from uuid import uuid4

async def setup():
    # Ensure tables exist
    print('[1/4] Ensuring tables exist...')
    await init_db()
    print('  Tables OK')
    
    # Check for existing users
    print('[2/4] Checking for existing users...')
    async with async_session_factory() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM users'))
        count = result.scalar()
        print(f'  Users found: {count}')
        
        if count > 0:
            result = await session.execute(text('SELECT email, role FROM users'))
            users = result.fetchall()
            for u in users:
                print(f'    - {u[0]} ({u[1]})')
            print('  No action needed - users exist')
            return
    
    # Create default admin user
    print('[3/4] Creating default admin user...')
    async with async_session_factory() as session:
        # Create tenant
        tenant = Tenant(
            id=uuid4(),
            name='Default Organization',
            slug='default-org',
            settings={},
            subscription_tier='enterprise',
        )
        session.add(tenant)
        await session.flush()
        print(f'  Tenant created: {tenant.name}')
        
        # Create admin user
        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email='admin@example.com',
            hashed_password=get_password_hash('password123'),
            full_name='Admin User',
            role='admin',
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()
        print(f'  Admin user created: {user.email}')
        
        # Create default roles
        for role_def in Role.get_default_roles():
            role = Role(**role_def)
            session.add(role)
        print('  Default roles created')
        
        await session.commit()
        print('  Changes committed')
    
    print('[4/4] Verifying...')
    async with async_session_factory() as session:
        result = await session.execute(text('SELECT email, role FROM users'))
        users = result.fetchall()
        for u in users:
            print(f'    - {u[0]} ({u[1]})')
    
    print('')
    print('=== SETUP COMPLETE ===')
    print('')
    print('You can now login with:')
    print('  Email: admin@example.com')
    print('  Password: password123')
    print('')
    print('Start the server with:')
    print('  cd C:\\Users\\antho\\clawd\\office-manager-api')
    print('  python -B -m uvicorn app.main:app --host 0.0.0.0 --port 8000')

if __name__ == '__main__':
    asyncio.run(setup())
