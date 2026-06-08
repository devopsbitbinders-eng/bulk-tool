"""
Final cleanup - saare duplicates delete karo, sirf ek 30 May rakhna hai
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from databases import Database
from dotenv import load_dotenv
import os

load_dotenv()

async def final_cleanup():
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///campaigns.db")
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://", 1)
    if "charset" not in DATABASE_URL and "mysql" in DATABASE_URL:
        DATABASE_URL += "?charset=utf8mb4"
    
    db = Database(DATABASE_URL)
    await db.connect()
    print("Connected!")
    
    # ID 138 delete karo (duplicate 30 May)
    await db.execute("DELETE FROM messages WHERE campaign_id = 138")
    await db.execute("DELETE FROM campaigns WHERE id = 138")
    print("Deleted duplicate ID 138 (30 May duplicate)")
    
    # ID 136 ka naam sahi karo
    await db.execute(
        "UPDATE campaigns SET name = 'Campaign 30 May - Imp Member Sheet42' WHERE id = 136"
    )
    print("Updated ID 136 name")
    
    # Final check
    print("\nFinal campaigns (19 May ke baad):")
    final = await db.fetch_all("""
        SELECT id, name, timestamp, total_numbers, sent_success, status 
        FROM campaigns 
        WHERE timestamp >= '2026-05-19 00:00:00'
        ORDER BY timestamp ASC
    """)
    for c in final:
        print(f"  ID {c['id']}: {c['name']} | {str(c['timestamp'])[:10]} | {c['total_numbers']} records | {c['status']}")
    
    await db.disconnect()
    print("\nCleanup done! Vercel dashboard refresh karo.")

if __name__ == "__main__":
    asyncio.run(final_cleanup())
