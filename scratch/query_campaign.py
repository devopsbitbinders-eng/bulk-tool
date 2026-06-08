import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from database import db

async def main():
    await db.connect()
    # Find message 65420
    m = await db.fetch_one("SELECT * FROM messages WHERE id = 65420")
    if m:
        m = dict(m)
        print("Message ID 65420:")
        print("  Campaign ID:", m.get("campaign_id"))
        print("  Error:", m.get("error_message"))
        print("  Row Data:", m.get("row_data"))
        
        # Get campaign details
        c = await db.fetch_one("SELECT * FROM campaigns WHERE id = :id", {"id": m.get("campaign_id")})
        if c:
            c = dict(c)
            print("Campaign Details:")
            print("  Name:", c.get("name"))
            print("  Template Name:", c.get("template_name"))
            print("  Mappings:", c.get("mappings"))
            print("  Media URL:", c.get("media_url"))
            print("  Meta Media ID:", c.get("meta_media_id"))
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
