"""
Duplicate campaigns clean karo aur restored campaigns ko proper names do
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from databases import Database
from dotenv import load_dotenv
import os

load_dotenv()

async def fix_campaigns():
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///campaigns.db")
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://", 1)
    if "charset" not in DATABASE_URL and "mysql" in DATABASE_URL:
        DATABASE_URL += "?charset=utf8mb4"
    
    db = Database(DATABASE_URL)
    await db.connect()
    print("Connected!\n")
    
    # 1. Saare campaigns dekho
    all_camps = await db.fetch_all(
        "SELECT id, name, timestamp, total_numbers, status FROM campaigns ORDER BY id DESC LIMIT 20"
    )
    print("Current campaigns:")
    for c in all_camps:
        print(f"  ID {c['id']}: {c['name']} | {c['timestamp']} | {c['total_numbers']} records")
    
    # 2. Duplicate Campaign 29 May delete karo (ID 137 rakhenge, 135 delete karenge)
    # Jo naya zyada ho usse delete karo (duplicate)
    print("\nDuplicates clean kar raha hun...")
    
    # Campaign 29 May ke saare IDs dhundo
    may29_camps = await db.fetch_all(
        "SELECT id FROM campaigns WHERE name = 'Campaign 29 May' ORDER BY id ASC"
    )
    if len(may29_camps) > 1:
        # Pehle wala rakhenge, baad wale delete karenge
        keep_id = may29_camps[0]['id']
        for c in may29_camps[1:]:
            del_id = c['id']
            await db.execute("DELETE FROM messages WHERE campaign_id = :id", {"id": del_id})
            await db.execute("DELETE FROM campaigns WHERE id = :id", {"id": del_id})
            print(f"  Deleted duplicate Campaign 29 May (ID: {del_id}), kept ID: {keep_id}")
    
    # 3. Restored campaigns ko better names do
    updates = [
        {"id": None, "name": "Campaign 29 May", "new_name": "Campaign 29 May - Imp Member", 
         "phone_col": "phone", "timestamp": "2026-05-29 10:00:00"},
        {"id": None, "name": "Campaign 30 May (Aaj)", "new_name": "Campaign 30 May - Imp Member",
         "phone_col": "phone", "timestamp": "2026-05-30 10:00:00"},
    ]
    
    for u in updates:
        camp = await db.fetch_one(
            "SELECT id FROM campaigns WHERE name = :name", {"name": u['name']}
        )
        if camp:
            await db.execute(
                "UPDATE campaigns SET name = :new_name, phone_col = :phone_col WHERE id = :id",
                {"new_name": u['new_name'], "phone_col": u['phone_col'], "id": camp['id']}
            )
            print(f"  Updated: '{u['name']}' -> '{u['new_name']}'")
    
    # 4. Final list
    print("\nFinal campaigns list:")
    final = await db.fetch_all(
        "SELECT id, name, timestamp, total_numbers, sent_success, status FROM campaigns ORDER BY timestamp DESC LIMIT 15"
    )
    for c in final:
        print(f"  ID {c['id']}: {c['name']} | {c['timestamp']} | {c['total_numbers']} total | {c['sent_success']} sent | {c['status']}")
    
    await db.disconnect()
    print("\nDone! Ab Vercel dashboard refresh karo.")

if __name__ == "__main__":
    asyncio.run(fix_campaigns())
