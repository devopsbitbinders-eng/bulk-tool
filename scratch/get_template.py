from dotenv import load_dotenv
load_dotenv()
import asyncio
import database
import json

async def check():
    await database.db.connect()
    res = await database.db.fetch_all("SELECT name, components FROM templates")
    for r in res:
        if r['components'] and 'Seva ka har yogdan' in r['components']:
            print(f"Name: {r['name']}")
            print(r['components'])
            print("---")

if __name__ == '__main__':
    asyncio.run(check())
