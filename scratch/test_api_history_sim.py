import asyncio
import os
import sqlite3
from http.cookies import SimpleCookie

async def check():
    # We don't have the user's session token directly, but we can query the DB to get it.
    import databases
    db = databases.Database("mysql+aiomysql://u802557144_bulk_testing:Bulktesting123@auth-db2053.hstgr.io:3306/u802557144_bulk_testing")
    await db.connect()
    
    # We'll just run the exact query that get_history runs for the user
    # First get the user id
    u = await db.fetch_one("SELECT id FROM users WHERE username = 'kajal_demo'")
    if not u:
        u = await db.fetch_one("SELECT id FROM users LIMIT 1")
    
    u_id = u['id']
    print(f"User ID: {u_id}")
    
    q = """
        SELECT c.id, c.name, c.timestamp, 
               COALESCE(NULLIF(c.total_numbers, 0), (SELECT COUNT(DISTINCT phone) FROM messages WHERE campaign_id = c.id)) as total_numbers, 
               c.status as campaign_status,
               COALESCE(c.message_template, (SELECT content FROM templates WHERE name = c.template_name LIMIT 1)) as message_template, c.msg_type,
               (SELECT COUNT(DISTINCT phone) FROM messages WHERE campaign_id = c.id AND (status = 'sent' OR status = 'delivered' OR status = 'read')) as sent_success,
               (SELECT COUNT(DISTINCT phone) FROM messages WHERE campaign_id = c.id AND status = 'delivered') as delivered,
               (SELECT COUNT(DISTINCT phone) FROM messages WHERE campaign_id = c.id AND status = 'read') as `read`,
               (SELECT COUNT(DISTINCT phone) FROM messages WHERE campaign_id = c.id AND status = 'failed') as failed
        FROM campaigns c 
        WHERE c.user_id = :u
        ORDER BY timestamp DESC
        LIMIT 5
    """
    rows = await db.fetch_all(q, {"u": u_id})
    for r in rows:
        d = dict(r)
        print(d)

asyncio.run(check())
