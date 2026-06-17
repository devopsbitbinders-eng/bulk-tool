import asyncio
import database
import time
import datetime

async def test():
    await database.db.connect()
    user_id = 1
    
    t0 = time.time()
    
    start_str_utc = '2026-05-10 00:00:00'
    end_str_utc = '2026-06-10 23:59:59'
    
    out = await database.db.fetch_one(
        "SELECT COUNT(*) as count FROM messages WHERE user_id = :u AND status IN ('sent', 'delivered', 'read') AND timestamp >= :s AND timestamp <= :e", 
        {"u": user_id, "s": start_str_utc, "e": end_str_utc}
    )
    print("Messages count:", dict(out))
    
    query = """
        SELECT DATE_FORMAT(DATE_ADD(timestamp, INTERVAL '5:30' HOUR_MINUTE), '%d %b') as day_str,
               status, COUNT(*) as cnt
        FROM messages
        WHERE user_id = :u AND timestamp >= :s AND timestamp <= :e
        GROUP BY day_str, status
    """
    agg = await database.db.fetch_all(query, {"u": user_id, "s": start_str_utc, "e": end_str_utc})
    print("Agg records:", len(agg))
    
    t1 = time.time()
    print("Time taken:", t1 - t0)

if __name__ == '__main__':
    asyncio.run(test())
