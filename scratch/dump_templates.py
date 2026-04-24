import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()
from database import get_db

async def check():
    db = await get_db()
    rows = await db.fetch_all("SELECT name, components FROM templates")
    for r in rows:
        print(f"TEMPLATE_NAME: {r['name']}")
        print(f"COMPONENTS_JSON: {r['components']}")
        print("="*40)

if __name__ == "__main__":
    asyncio.run(check())
