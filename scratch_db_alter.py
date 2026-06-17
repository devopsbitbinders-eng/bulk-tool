import asyncio
from dotenv import load_dotenv
load_dotenv()
from database import get_db

async def run():
    db = await get_db()
    try:
        await db.execute("ALTER TABLE user_credentials ADD COLUMN alert_phone TEXT")
        print("Column added successfully.")
    except Exception as e:
        print(f"Error adding column: {e}")

asyncio.run(run())
