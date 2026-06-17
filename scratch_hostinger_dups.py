import asyncio
import os
from dotenv import load_dotenv

# Load before anything else!
load_dotenv()

from database import db

async def main():
    await db.connect()
    campaigns = await db.fetch_all('SELECT id FROM campaigns ORDER BY id DESC LIMIT 5')
    for c in campaigns:
        msgs = await db.fetch_all('SELECT COUNT(*) as cnt, phone FROM messages WHERE campaign_id = :c GROUP BY phone HAVING cnt > 1', {'c': c['id']})
        if msgs:
            print(f"Campaign {c['id']} HAS DUPLICATES! Count of duplicate numbers: {len(msgs)}")
            print(f"Sample duplicate rows for campaign {c['id']}:", [dict(m) for m in msgs[:2]])
        else:
            print(f"Campaign {c['id']} has NO duplicates.")
            
    # Check if unique index exists
    try:
        indexes = await db.fetch_all("SHOW INDEXES FROM messages")
        idx_names = [i['Key_name'] for i in indexes]
        print("Indexes on messages:", set(idx_names))
    except Exception as e:
        print("Could not fetch indexes:", e)
        
    await db.disconnect()

asyncio.run(main())
