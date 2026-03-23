import asyncio
import os
from database import db, DATABASE_URL

async def migrate():
    print(f"Connecting to {DATABASE_URL}...")
    await db.connect()
    
    is_mysql = DATABASE_URL.startswith("mysql")
    if not is_mysql:
        print("This script is specifically for MySQL migration. SQLite supports emojis by default.")
        await db.disconnect()
        return

    tables = ["campaigns", "messages", "templates", "user_credentials"]
    
    print("--- Starting utf8mb4 Migration ---")
    
    # 1. Database level
    try:
        db_name = DATABASE_URL.split('/')[-1].split('?')[0]
        await db.execute(f"ALTER DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ Database {db_name} converted to utf8mb4")
    except Exception as e:
        print(f"✗ Failed to convert database: {e}")

    # 2. Table level
    for table in tables:
        try:
            await db.execute(f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✓ Table '{table}' converted to utf8mb4")
        except Exception as e:
            print(f"✗ Failed to convert table {table}: {e}")

    print("--- Migration Complete ---")
    print("Verification: Try sending 'Hey 👋' now. If it works, the migration was successful.")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate())
