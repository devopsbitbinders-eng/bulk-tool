import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()
from database import get_db

async def check_templates():
    db = await get_db()
    rows = await db.fetch_all("SELECT name, components FROM templates LIMIT 10")
    for r in rows:
        print(f"Template: {r['name']}")
        print(f"Components: {r['components']}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_templates())
