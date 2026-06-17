import asyncio
from databases import Database

DATABASE_URL="mysql+aiomysql://u802557144_bulk_testing:Bulktesting123@auth-db2053.hstgr.io:3306/u802557144_bulk_testing"
db = Database(DATABASE_URL)

async def test():
    await db.connect()
    rows = await db.fetch_all("SELECT status, COUNT(*) as c FROM messages WHERE campaign_id = 154 GROUP BY status")
    for r in rows:
        print(dict(r))

asyncio.run(test())
