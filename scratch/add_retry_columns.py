"""
Migration: Add retry_count and next_retry_at columns to messages table
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from databases import Database
from dotenv import load_dotenv
import os

load_dotenv()

async def migrate():
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://", 1)
    if "charset" not in DATABASE_URL and "mysql" in DATABASE_URL:
        DATABASE_URL += "?charset=utf8mb4"
    
    db = Database(DATABASE_URL)
    await db.connect()
    print("Connected!")
    
    # Add retry_count column
    try:
        await db.execute("ALTER TABLE messages ADD COLUMN retry_count INT DEFAULT 0")
        print("✅ Added retry_count column")
    except Exception as e:
        if "Duplicate column" in str(e):
            print("⚠️  retry_count already exists")
        else:
            print(f"❌ retry_count error: {e}")
    
    # Add next_retry_at column
    try:
        await db.execute("ALTER TABLE messages ADD COLUMN next_retry_at DATETIME NULL DEFAULT NULL")
        print("✅ Added next_retry_at column")
    except Exception as e:
        if "Duplicate column" in str(e):
            print("⚠️  next_retry_at already exists")
        else:
            print(f"❌ next_retry_at error: {e}")
    
    # Add index for faster retry queries
    try:
        await db.execute("CREATE INDEX idx_retry ON messages (status, retry_count, next_retry_at)")
        print("✅ Added index idx_retry")
    except Exception as e:
        if "Duplicate" in str(e):
            print("⚠️  Index already exists")
        else:
            print(f"⚠️  Index error (non-critical): {e}")
    
    await db.disconnect()
    print("\nMigration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
