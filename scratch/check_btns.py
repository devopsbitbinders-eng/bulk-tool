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
        has_btns = any(c.get('type') == 'BUTTONS' for c in comps)
        print("Has Buttons:", has_btns)
        if has_btns:
            print(comps)
    else:
        print("No components or not found")

if __name__ == '__main__':
    asyncio.run(check())
