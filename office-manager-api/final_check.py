import sys
sys.path.insert(0, 'C:/Users/antho/clawd/office-manager-api')

print('=== FINAL DIAGNOSTIC ===')
print('')

import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def check():
    # 1. Check database
    print('[1/3] Database')
    async with async_session_factory() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM users'))
        users = result.scalar()
        print(f'  Users: {users}')
        
        if users > 0:
            result = await session.execute(text('SELECT email, role FROM users'))
            for u in result.fetchall():
                print(f'  - {u[0]} ({u[1]})')
    
    # 2. Check password hash
    print('')
    print('[2/3] Password Hash')
    from app.core.security import get_password_hash, verify_password
    test_hash = get_password_hash('password123')
    works = verify_password('password123', test_hash)
    print(f'  Hash works: {works}')
    
    # 3. Check JWT
    print('')
    print('[3/3] JWT Token')
    from app.core.security import create_access_token
    from datetime import timedelta
    token = create_access_token(
        data={'sub': 'test', 'tenant_id': 'test', 'role': 'admin'},
        expires_delta=timedelta(minutes=30)
    )
    print(f'  Token created: {token[:30]}...')
    
    print('')
    print('=== READY FOR TOMORROW ===')
    print('')
    print('Start server:')
    print('  cd C:\\Users\\antho\\clawd\\office-manager-api')
    print('  python -B -m uvicorn app.main:app --host 0.0.0.0 --port 8000')
    print('')
    print('Login:')
    print('  Email: admin@example.com')
    print('  Password: password123')

if __name__ == '__main__':
    asyncio.run(check())
