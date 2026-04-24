import asyncio
import os
from databases import Database

async def check_local_db():
    db = Database("sqlite:///campaigns.db")
    await db.connect()
    try:
        rows = await db.fetch_all("SELECT id, name, status, timestamp FROM campaigns ORDER BY timestamp DESC LIMIT 5")
        print("LOCAL SQLITE CAMPAIGNS:")
        for r in rows:
            print(dict(r))
    except Exception as e:
        print(f"Error checking SQLite: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_local_db())
