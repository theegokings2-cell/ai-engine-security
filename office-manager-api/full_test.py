import sys
sys.path.insert(0, 'C:/Users/antho/clawd/office-manager-api')

print('=== FULL SYSTEM TEST ===')
print('')

import asyncio
import subprocess
import time
import aiohttp
import json

async def test():
    # 1. Ensure database has admin user
    print('[1/4] Checking database...')
    from sqlalchemy import text
    from app.db.session import async_session_factory
    
    async with async_session_factory() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM users'))
        users = result.scalar()
        print(f'    Users in DB: {users}')
        if users == 0:
            print('    ERROR: No users - run create_admin.py first!')
            return False
        print('    OK')
    
    # 2. Start server in background
    print('[2/4] Starting server...')
    server_proc = subprocess.Popen(
        [sys.executable, '-B', '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
        cwd='C:/Users/antho/clawd/office-manager-api',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    print('    Waiting for server...')
    await asyncio.sleep(5)
    
    # 3. Test login
    print('[3/4] Testing login...')
    url = "http://localhost:8000/api/v1/auth/login"
    data = {"username": "admin@example.com", "password": "password123"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    text_data = await response.text()
                    result = json.loads(text_data)
                    token = result.get('access_token', '')
                    print(f'    Status: 200 OK')
                    print(f'    Token received: {token[:30]}...')
                    print('    OK')
                else:
                    text_data = await response.text()
                    print(f'    Status: {response.status}')
                    print(f'    Error: {text_data}')
                    server_proc.terminate()
                    return False
    except Exception as e:
        print(f'    ERROR: {e}')
        server_proc.terminate()
        return False
    
    # 4. Test protected endpoint
    print('[4/4] Testing /me endpoint...')
    me_url = "http://localhost:8000/api/v1/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(me_url, headers=headers) as response:
                if response.status == 200:
                    text_data = await response.text()
                    user = json.loads(text_data)
                    print(f'    Email: {user.get("email")}')
                    print(f'    Role: {user.get("role")}')
                    print('    OK')
                else:
                    print(f'    Status: {response.status}')
                    print(f'    Error: {await response.text()}')
    except Exception as e:
        print(f'    ERROR: {e}')
    
    # Cleanup
    server_proc.terminate()
    
    print('')
    print('=== ALL TESTS PASSED ===')
    print('')
    print('Tomorrow:')
    print('  1. cd C:\\Users\\antho\\clawd\\office-manager-api')
    print('  2. python -B -m uvicorn app.main:app --host 0.0.0.0 --port 8000')
    print('  3. Login: admin@example.com / password123')
    return True

if __name__ == '__main__':
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
