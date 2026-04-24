import asyncio
import os
from database import get_db

async def check_campaigns():
    db = await get_db()
    rows = await db.fetch_all("SELECT id, name, status, timestamp FROM campaigns ORDER BY timestamp DESC LIMIT 5")
    print("LAST 5 CAMPAIGNS:")
    for r in rows:
        print(dict(r))

if __name__ == "__main__":
    asyncio.run(check_campaigns())
