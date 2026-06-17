import asyncio
import json
from database import get_db

async def main():
    db = await get_db()
    logs = await db.fetch_all("SELECT payload FROM webhook_logs ORDER BY id DESC LIMIT 15")
    for log in logs:
        print("-------------")
        try:
            print(json.dumps(json.loads(log['payload']), indent=2))
        except:
            pass

asyncio.run(main())
