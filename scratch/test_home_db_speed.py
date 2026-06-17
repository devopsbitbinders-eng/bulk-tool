import asyncio
import database
import time
from dotenv import load_dotenv

load_dotenv()

async def test():
    await database.db.connect()
    user_id = 1
    
    t0 = time.time()
    
    out = await database.db.fetch_all("""
            SELECT c.*,
                SUM(CASE WHEN m.status IN ('failed', 'sent', 'delivered', 'read') THEN 1 ELSE 0 END) as sent_success_combined,
                SUM(CASE WHEN m.status = 'delivered' THEN 1 ELSE 0 END) as delivered_count,
                SUM(CASE WHEN m.status = 'read' THEN 1 ELSE 0 END) as read_count,
                SUM(CASE WHEN m.status = 'failed' THEN 1 ELSE 0 END) as failed_count
            FROM (SELECT * FROM campaigns WHERE user_id = :u ORDER BY timestamp DESC LIMIT 50) c
            LEFT JOIN messages m ON m.campaign_id = c.id
            GROUP BY c.id
            ORDER BY c.timestamp DESC
        """, {"u": user_id})
    print("Campaigns fetched:", len(out))
    
    t1 = time.time()
    print("Time taken:", t1 - t0)

if __name__ == '__main__':
    asyncio.run(test())
