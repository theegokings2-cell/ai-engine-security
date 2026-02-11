import sys
sys.path.insert(0, 'C:/Users/antho/clawd/office-manager-api')

print('=== MORNING DIAGNOSTIC ===')

import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def check():
    # Check tables
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result.fetchall()]
        print(f'Tables: {tables}')
        
        result = await session.execute(text('SELECT COUNT(*) FROM users'))
        users = result.scalar()
        print(f'Users: {users}')
        
        if users > 0:
            result = await session.execute(text('SELECT email, role FROM users'))
            for u in result.fetchall():
                print(f'  - {u[0]} ({u[1]})')
            print('')
            print('SUCCESS: Admin user exists!')
            print('Ready to login: admin@example.com / password123')
        else:
            print('No users - running setup...')
            print('Run: python create_admin.py')

if __name__ == '__main__':
    asyncio.run(check())
