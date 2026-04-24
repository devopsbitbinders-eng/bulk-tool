import asyncio
from database import db, init_db

async def migrate_business_name():
    await db.connect()
    print("Migrating database to add business_name column...")
    
    is_mysql = str(db.url.scheme).lower().startswith("mysql")
    
    try:
        if is_mysql:
            await db.execute("ALTER TABLE users ADD COLUMN business_name VARCHAR(255) AFTER username")
        else:
            await db.execute("ALTER TABLE users ADD COLUMN business_name TEXT")
        print("Success: Added business_name column to users table.")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e):
            print("Notice: Column business_name already exists.")
        else:
            print(f"Error during migration: {e}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate_business_name())
