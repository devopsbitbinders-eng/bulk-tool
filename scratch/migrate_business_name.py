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
        print("Success: Added business_name column.")
    except Exception as e:
        print(f"Notice (business_name): {e}")

    try:
        if is_mysql:
            await db.execute("ALTER TABLE users ADD COLUMN expiry_date DATETIME AFTER is_admin")
        else:
            await db.execute("ALTER TABLE users ADD COLUMN expiry_date DATETIME")
        print("Success: Added expiry_date column.")
    except Exception as e:
        print(f"Notice (expiry_date): {e}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate_business_name())
