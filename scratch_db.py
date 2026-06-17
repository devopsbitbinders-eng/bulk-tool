import asyncio
from dotenv import load_dotenv
load_dotenv()
from database import get_db

async def run():
    db = await get_db()
    rows = await db.fetch_all("SELECT phone_number, alert_phone FROM user_credentials WHERE user_id=10")
    for r in rows:
        print(dict(r))

asyncio.run(run())
