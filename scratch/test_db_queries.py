import asyncio
import datetime
from databases import Database

DATABASE_URL="mysql+aiomysql://u802557144_bulk_testing:Bulktesting123@auth-db2053.hstgr.io:3306/u802557144_bulk_testing"
db = Database(DATABASE_URL)

async def test():
    await db.connect()
    
    user = await db.fetch_one("SELECT id FROM users LIMIT 1")
    if not user:
        print("No users found")
        return
        
    start = "2026-06-04"
    end = "2026-06-10"
    ist_delta = datetime.timedelta(hours=5, minutes=30)
    
    start_dt_ist = datetime.datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=datetime.timezone(ist_delta))
    end_dt_ist = datetime.datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone(ist_delta))
    
    start_str_utc = start_dt_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    end_str_utc = end_dt_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    print("Executing queries...")
    try:
        inc = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE user_id = :u AND direction='inbound' AND timestamp >= :s AND timestamp <= :e", {"u": user['id'], "s": start_str_utc, "e": end_str_utc})
        print("Inc:", inc)
    except Exception as e:
        print("Inc Error:", type(e), str(e))
        
    try:
        out = await db.fetch_one("SELECT COUNT(*) as count FROM messages WHERE user_id = :u AND status IN ('sent', 'delivered', 'read') AND timestamp >= :s AND timestamp <= :e", {"u": user['id'], "s": start_str_utc, "e": end_str_utc})
        print("Out:", out)
    except Exception as e:
        print("Out Error:", type(e), str(e))
        
    try:
        out_records = await db.fetch_all("SELECT timestamp, status FROM messages WHERE user_id = :u AND timestamp >= :s AND timestamp <= :e", {"u": user['id'], "s": start_str_utc, "e": end_str_utc})
        print("Out Records:", len(out_records))
        if out_records:
            print("First record:", out_records[0])
    except Exception as e:
        print("Records Error:", type(e), str(e))

asyncio.run(test())
