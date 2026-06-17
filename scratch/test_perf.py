import asyncio
import time
import os
import sys

root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from database import get_db

async def test():
    db = await get_db()
    
    # User 1 for test
    u_id = 1
    params = {"u": u_id}
    inner_query = "SELECT * FROM campaigns WHERE user_id = :u ORDER BY timestamp DESC LIMIT 500"
    
    # 1. Join + Group By
    t0 = time.time()
    await db.fetch_all(f"""
        SELECT c.id, c.name, c.timestamp, c.template_name, c.media_url,
               COALESCE(NULLIF(c.total_numbers, 0), COUNT(m.id)) as total_numbers, 
               c.status as campaign_status,
               COALESCE(c.message_template, (SELECT content FROM templates WHERE name = c.template_name LIMIT 1)) as message_template, 
               (SELECT components FROM templates WHERE name = c.template_name LIMIT 1) as template_components,
               (SELECT media_url FROM templates WHERE name = c.template_name LIMIT 1) as t_media_url,
               c.msg_type,
               SUM(CASE WHEN m.status = 'sent' THEN 1 ELSE 0 END) as sent_success,
               SUM(CASE WHEN m.status = 'delivered' THEN 1 ELSE 0 END) as delivered,
               SUM(CASE WHEN m.status = 'read' THEN 1 ELSE 0 END) as `read`,
               SUM(CASE WHEN m.status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM ({inner_query}) c 
        LEFT JOIN messages m ON m.campaign_id = c.id
        GROUP BY c.id
        ORDER BY c.timestamp DESC
    """, params)
    print(f"Join time: {time.time() - t0:.4f}s")

    # 2. Subselects
    t0 = time.time()
    await db.fetch_all(f"""
        SELECT c.id, c.name, c.timestamp, c.template_name, c.media_url,
               COALESCE(NULLIF(c.total_numbers, 0), (SELECT COUNT(id) FROM messages WHERE campaign_id = c.id)) as total_numbers, 
               c.status as campaign_status,
               COALESCE(c.message_template, (SELECT content FROM templates WHERE name = c.template_name LIMIT 1)) as message_template, 
               (SELECT components FROM templates WHERE name = c.template_name LIMIT 1) as template_components,
               (SELECT media_url FROM templates WHERE name = c.template_name LIMIT 1) as t_media_url,
               c.msg_type,
               (SELECT COUNT(id) FROM messages WHERE campaign_id = c.id AND status = 'sent') as sent_success,
               (SELECT COUNT(id) FROM messages WHERE campaign_id = c.id AND status = 'delivered') as delivered,
               (SELECT COUNT(id) FROM messages WHERE campaign_id = c.id AND status = 'read') as `read`,
               (SELECT COUNT(id) FROM messages WHERE campaign_id = c.id AND status = 'failed') as failed
        FROM ({inner_query}) c 
        ORDER BY c.timestamp DESC
    """, params)
    print(f"Subselects time: {time.time() - t0:.4f}s")

asyncio.run(test())
