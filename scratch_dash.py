import asyncio
from database import get_db, database as db
import datetime

async def test():
    await db.connect()
    
    # Fake user
    user = {'id': 1}
    ist_delta = datetime.timedelta(hours=5, minutes=30)
    
    start = '2026-06-03'
    end = '2026-06-09'
    
    start_dt_ist = datetime.datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=datetime.timezone(ist_delta))
    end_dt_ist = datetime.datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone(ist_delta))
    start_str_utc = start_dt_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    end_str_utc = end_dt_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    out = await db.fetch_all("SELECT timestamp, status FROM messages WHERE user_id = :u AND timestamp >= :s AND timestamp <= :e", {"u": user['id'], "s": start_str_utc, "e": end_str_utc})
    
    print(len(out))

asyncio.run(test())
