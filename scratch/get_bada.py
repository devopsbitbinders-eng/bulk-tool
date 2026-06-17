from dotenv import load_dotenv
load_dotenv()
import asyncio
import database
import json

async def check():
    await database.db.connect()
    res = await database.db.fetch_all("SELECT * FROM templates WHERE name = 'bada_mangal' LIMIT 1")
    for r in res:
        print("Name:", r['name'])
        print("Components:", r['components'])
        print("---")

if __name__ == '__main__':
    asyncio.run(check())
