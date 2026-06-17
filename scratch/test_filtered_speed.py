import asyncio
import database
import time
from dotenv import load_dotenv

load_dotenv()

async def test():
    await database.db.connect()
    user_id = 1
    
    t0 = time.time()
    start_str_utc = '2026-05-10 00:00:00'
    end_str_utc = '2026-06-10 23:59:59'
    
    out_records = await database.db.fetch_all("SELECT timestamp, status FROM messages WHERE user_id = :u AND timestamp >= :s AND timestamp <= :e", {"u": user_id, "s": start_str_utc, "e": end_str_utc})
    
    t1 = time.time()
    print("Time taken:", t1 - t0)

if __name__ == '__main__':
    asyncio.run(test())
