import asyncio
from databases import Database

DATABASE_URL="mysql+aiomysql://u802557144_bulk_testing:Bulktesting123@auth-db2053.hstgr.io:3306/u802557144_bulk_testing"
db = Database(DATABASE_URL)

async def test():
    await db.connect()
    
    q = """
        SELECT c.id, c.name, 
               c.total_numbers as orig_total,
               (SELECT COUNT(DISTINCT phone) FROM messages WHERE campaign_id = c.id) as subquery_total,
               COALESCE(NULLIF(c.total_numbers, 0), (SELECT COUNT(DISTINCT phone) FROM messages WHERE campaign_id = c.id)) as total_numbers,
               c.template_name,
               (SELECT content FROM templates WHERE name = c.template_name LIMIT 1) as tpl_content,
               COALESCE(c.message_template, (SELECT content FROM templates WHERE name = c.template_name LIMIT 1)) as message_template
        FROM campaigns c
        LIMIT 5
    """
    rows = await db.fetch_all(q)
    for r in rows:
        print(dict(r))

asyncio.run(test())
