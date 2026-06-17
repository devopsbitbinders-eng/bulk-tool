from dotenv import load_dotenv
load_dotenv()
import asyncio
import database
import json

async def check():
    await database.db.connect()
    res = await database.db.fetch_one("SELECT components FROM templates WHERE name='monthyl_expense'")
    if res and res['components']:
        comps = json.loads(res['components'])
        footer = next((c for c in comps if c['type'] == 'FOOTER'), None)
        print("Has Footer:", bool(footer))
        if footer:
            print("Footer text:", footer.get('text'))
    else:
        print("No components")

if __name__ == '__main__':
    asyncio.run(check())
