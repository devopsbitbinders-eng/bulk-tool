import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import asyncio
from main import get_filtered_dashboard, get_db

class MockRequest:
    def __init__(self):
        self.cookies = {}

async def main():
    try:
        db = await get_db()
        user = await db.fetch_one("SELECT * FROM users LIMIT 1")
        if user:
            r = MockRequest()
            r.cookies['session_token'] = user['session_token']
            res = await get_filtered_dashboard(r, '2026-05-10', '2026-06-08')
            print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
