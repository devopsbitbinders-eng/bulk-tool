"""
Database ka current state check karo - saare campaigns 19 May ke baad
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from databases import Database
from dotenv import load_dotenv
import os

load_dotenv()

async def check_state():
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///campaigns.db")
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://", 1)
    if "charset" not in DATABASE_URL and "mysql" in DATABASE_URL:
        DATABASE_URL += "?charset=utf8mb4"
    
    db = Database(DATABASE_URL)
    await db.connect()
    
    print("=" * 70)
    print("DATABASE ME SAARE CAMPAIGNS (19 May ke baad):")
    print("=" * 70)
    
    camps = await db.fetch_all("""
        SELECT id, name, timestamp, total_numbers, sent_success, sent_failed, status
        FROM campaigns 
        WHERE timestamp >= '2026-05-19 00:00:00'
        ORDER BY timestamp ASC
    """)
    
    for c in camps:
        msg_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM messages WHERE campaign_id = :id", {"id": c['id']}
        )
        print(f"\n  ID: {c['id']}")
        print(f"  Name: {c['name']}")
        print(f"  Date: {c['timestamp']}")
        print(f"  Total: {c['total_numbers']} | Success: {c['sent_success']} | Status: {c['status']}")
        print(f"  Messages in DB: {msg_count['cnt']}")
    
    print("\n" + "=" * 70)
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_state())
