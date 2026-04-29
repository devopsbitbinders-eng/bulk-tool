import asyncio
from database import db

async def migrate():
    print("Starting template table migration...")
    await db.connect()
    try:
        # For MySQL
        try:
            await db.execute("ALTER TABLE templates DROP INDEX `user_id`")
            print("Dropped old unique index (MySQL)")
        except:
            pass
            
        try:
            await db.execute("ALTER TABLE templates DROP INDEX `UNIQUE`")
        except:
            pass

        # Add new constraint
        try:
            await db.execute("CREATE UNIQUE INDEX idx_user_template_lang ON templates(user_id, name, language)")
            print("Created new unique index (user_id, name, language)")
        except Exception as e:
            print(f"Index creation notice: {e}")
            
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        await db.disconnect()
        print("Migration finished.")

if __name__ == "__main__":
    asyncio.run(migrate())
