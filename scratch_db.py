import asyncio
from databases import Database
import os
from dotenv import load_dotenv

load_dotenv()

async def run():
    db_url = os.environ.get("DATABASE_URL")
    if db_url.startswith("mysql://"):
        db_url = db_url.replace("mysql://", "mysql+aiomysql://", 1)
    db = Database(db_url)
    await db.connect()
    
    camps = await db.fetch_all("SELECT id, name FROM campaigns WHERE name LIKE '%Sheet62%' LIMIT 5")
    for camp in camps:
        print("Found campaign:", camp['id'], camp['name'])
            
    await db.disconnect()

asyncio.run(run())
