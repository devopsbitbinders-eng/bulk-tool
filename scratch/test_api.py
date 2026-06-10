from dotenv import load_dotenv
load_dotenv()
import asyncio
import database
import json

async def check():
    await database.db.connect()
    # Mock the exact query
    rows = await database.db.fetch_all("""
        SELECT c.id, c.name, c.timestamp, c.template_name, c.media_url,
               COALESCE(c.message_template, (SELECT content FROM templates WHERE name = c.template_name LIMIT 1)) as message_template, 
               (SELECT components FROM templates WHERE name = c.template_name LIMIT 1) as template_components
        FROM campaigns c
        WHERE c.name LIKE 'Imp Member - Sheet43%'
        LIMIT 1
    """)
    if not rows:
        print("No campaigns found")
        return
        
    for r in rows:
        d = dict(r)
        print("Template Components (Raw Type):", type(d['template_components']))
        print("Template Components (Raw):", d['template_components'])
        
        if d['template_components']:
            parsed = json.loads(d['template_components'])
            print("Parsed:", type(parsed))
            btns = [c for c in parsed if c['type'] == 'BUTTONS']
            print("Buttons found:", bool(btns))

if __name__ == '__main__':
    asyncio.run(check())
