import asyncio
from databases import Database

DATABASE_URL="mysql+aiomysql://u802557144_bulk_testing:Bulktesting123@auth-db2053.hstgr.io:3306/u802557144_bulk_testing"
db = Database(DATABASE_URL)

async def test():
    await db.connect()
    
    q = """
        SELECT c.id, c.name, c.total_numbers, c.message_template, c.template_name,
               (SELECT COUNT(DISTINCT phone) FROM messages WHERE campaign_id = c.id) as real_total
        FROM campaigns c
        LIMIT 5
    """
    rows = await db.fetch_all(q)
    for r in rows:
        print(dict(r))
        
    print("\nTemplates:")
    t_rows = await db.fetch_all("SELECT name, body FROM templates LIMIT 2")
    for r in t_rows:
        print(dict(r))

asyncio.run(test())
