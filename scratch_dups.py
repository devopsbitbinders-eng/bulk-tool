import asyncio
from database import db

async def main():
    await db.connect()
    c = await db.fetch_one('SELECT id FROM campaigns ORDER BY id DESC LIMIT 1')
    if c:
        msgs = await db.fetch_all('SELECT COUNT(*) as cnt, phone FROM messages WHERE campaign_id = :c GROUP BY phone HAVING cnt > 1', {'c': c['id']})
        print(f"Dups for campaign {c['id']}:", [dict(m) for m in msgs])
    else:
        print("No campaigns found.")
    await db.disconnect()

asyncio.run(main())
