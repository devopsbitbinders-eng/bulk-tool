import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from database import get_db

async def find_template():
    db = await get_db()
    # Get last campaign
    camp = await db.fetch_one("SELECT id, name FROM campaigns ORDER BY id DESC LIMIT 1")
    if camp:
        print(f"Last Campaign: {camp['id']} - {camp['name']}")
        # Find which template was used (need to look at logs or just assume the one that is active)
        # Actually, let's look at the messages table to see if we stored template name there (we don't)
        # Let's check the templates table for the user who owns this campaign
        owner = await db.fetch_one("SELECT user_id FROM campaigns WHERE id = :id", {"id": camp['id']})
        if owner:
            temps = await db.fetch_all("SELECT name, components FROM templates WHERE user_id = :u", {"u": owner['user_id']})
            for t in temps:
                print(f"User Template: {t['name']}")
                print(f"Components: {t['components']}")
                print("-" * 20)

if __name__ == "__main__":
    asyncio.run(find_template())
