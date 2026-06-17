import asyncio
from database import db

async def main():
    await db.connect()
    campaigns = await db.fetch_all('SELECT id FROM campaigns ORDER BY id DESC LIMIT 5')
    for c in campaigns:
        msgs = await db.fetch_all('SELECT COUNT(*) as cnt, phone FROM messages WHERE campaign_id = :c GROUP BY phone HAVING cnt > 1', {'c': c['id']})
        if msgs:
            print(f"Campaign {c['id']} HAS DUPLICATES! Count: {len(msgs)}")
        else:
            print(f"Campaign {c['id']} has NO duplicates.")
    await db.disconnect()

asyncio.run(main())
