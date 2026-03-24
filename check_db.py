import asyncio
import os
import sys
# Add current dir to sys.path
sys.path.append(os.getcwd())

from database import db, init_db

async def check():
    try:
        print("DEBUG: Manually initializing DB...")
        await init_db()
        
        await db.connect()
        print("Connected to DB")
        
        users = await db.fetch_all("SELECT id, username FROM users")
        print("\n--- USERS ---")
        for u in users:
            print(f"ID: {u['id']}, Username: {u['username']}")

        campaigns = await db.fetch_all("SELECT id, name, user_id, timestamp FROM campaigns ORDER BY timestamp DESC LIMIT 5")
        print("\n--- RECENT CAMPAIGNS ---")
        for c in campaigns:
            print(f"ID: {c['id']}, Name: {c['name']}, UserID: {c['user_id']}, Time: {c['timestamp']}")

        chat = await db.fetch_all("SELECT id, phone, user_id, direction FROM chat_messages ORDER BY id DESC LIMIT 5")
        print("\n--- RECENT CHAT MESSAGES ---")
        for m in chat:
            print(f"ID: {m['id']}, Phone: {m['phone']}, UserID: {m['user_id']}, Dir: {m['direction'] or 'N/A'}")

        creds = await db.fetch_all("SELECT id, user_id, phone_number FROM user_credentials ORDER BY id DESC")
        print("\n--- USER CREDENTIALS ---")
        for cr in creds:
            print(f"ID: {cr['id']}, UserID: {cr['user_id']}, Phone: {cr['phone_number']}")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check())
