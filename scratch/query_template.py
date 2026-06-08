import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from database import db
import json

async def main():
    await db.connect()
    res = await db.fetch_one("SELECT components FROM templates WHERE name = 'bada_magal_bhandara3'")
    if res:
        print("COMPONENTS:", res['components'])
    else:
        print("Template not found in local DB cache")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
