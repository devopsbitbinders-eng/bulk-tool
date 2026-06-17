import asyncio
import sys
import os
sys.path.append(os.getcwd())
from database import get_db

async def main():
    db = await get_db()
    count = await db.fetch_one("SELECT COUNT(*) as c FROM webhook_logs")
    print("TOTAL LOGS:", count['c'])

asyncio.run(main())
