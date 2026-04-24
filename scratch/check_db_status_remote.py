import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv() # Load from .env file

from database import get_db

async def check_messages():
    # Print what URL we are actually using
    from database import DATABASE_URL
    print(f"USING DATABASE: {DATABASE_URL}")
    
    db = await get_db()
    # Check the last 5 messages and their IDs
    rows = await db.fetch_all("SELECT id, phone, status, whatsapp_message_id, timestamp FROM messages ORDER BY timestamp DESC LIMIT 5")
    print("\nLAST 5 MESSAGES:")
    for r in rows:
        print(dict(r))
    
    # Check if there are any 'delivered' messages at all
    count = await db.fetch_one("SELECT COUNT(*) as count FROM messages WHERE status = 'delivered'")
    print(f"\nTOTAL DELIVERED MESSAGES: {count['count']}")

if __name__ == "__main__":
    asyncio.run(check_messages())
