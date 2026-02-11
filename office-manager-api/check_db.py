import asyncio
from sqlalchemy import text
from app.db.session import engine, async_session_factory

async def check_db():
    print('=== DATABASE CHECK ===')
    try:
        async with engine.begin() as conn:
            # Check if tables exist
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = [row[0] for row in result.fetchall()]
            print(f'Tables found: {tables}')
            
            # Check users
            result = await conn.execute(text('SELECT COUNT(*) FROM users'))
            users = result.scalar()
            print(f'Users: {users}')
            
    except Exception as e:
        print(f'DB Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_db())
