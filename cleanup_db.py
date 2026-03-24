import asyncio
from dotenv import load_dotenv
load_dotenv()
from database import get_db, init_db

async def cleanup():
    print("Connecting to database for cleanup...")
    await init_db()
    db = await get_db()
    
    print("Deleting 'test_template_duplicate'...")
    await db.execute("DELETE FROM templates WHERE name = 'test_template_duplicate'")
    
    print("Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(cleanup())
