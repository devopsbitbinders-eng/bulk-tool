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
    
    # Check MySQL CURRENT_TIMESTAMP
    row = await db.fetch_one("SELECT CURRENT_TIMESTAMP as db_time, @@time_zone as tz")
    print("Database Time:", row['db_time'])
    print("Timezone Config:", row['tz'])
    
    await db.disconnect()

asyncio.run(run())
