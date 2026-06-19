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
    
    rows = await db.fetch_all("SELECT COUNT(*) as c FROM chat_messages WHERE direction='outbound' AND timestamp >= '2026-06-18 18:30:00'")
    for r in rows:
        print("Chat Today:", r['c'])
        
    await db.disconnect()

asyncio.run(run())
