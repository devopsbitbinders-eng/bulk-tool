import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from database import get_db

async def migrate():
    db = await get_db()
    is_mysql = os.environ.get("DATABASE_URL", "").startswith("mysql")
    
    columns = [
        "message_template TEXT",
        "msg_type TEXT",
        "template_name TEXT",
        "language_code TEXT",
        "mappings TEXT",
        "phone_col TEXT"
    ]
    
    for col in columns:
        try:
            print(f"Adding column {col}...")
            await db.execute(f"ALTER TABLE campaigns ADD COLUMN {col}")
        except Exception as e:
            print(f"Column might already exist: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
