import sys
sys.path.insert(0, 'C:/Users/antho/clawd/office-manager-api')

print('=== LOGIN TEST ===')

import asyncio
import aiohttp

async def test_login():
    url = "http://localhost:8000/api/v1/auth/login"
    data = {"username": "admin@example.com", "password": "password123"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            text = await response.text()
            print(f"Status: {response.status}")
            print(f"Response: {text}")
            
            if response.status == 200:
                print("")
                print("SUCCESS: Login works!")
                import json
                token = json.loads(text).get('access_token', '')[:50]
                print(f"Token: {token}...")
            else:
                print("")
                print("FAILED: Login not working")

if __name__ == '__main__':
    asyncio.run(test_login())
