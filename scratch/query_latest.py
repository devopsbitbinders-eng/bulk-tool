import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from database import db

async def main():
    await db.connect()
    # Get the latest campaigns
    res = await db.fetch_all("SELECT * FROM campaigns ORDER BY id DESC LIMIT 5")
    for r in res:
        d = dict(r)
        print("Campaign ID:", d.get("id"))
        print("  Name:", d.get("name"))
        print("  Template Name:", d.get("template_name"))
        print("  Mappings:", d.get("mappings"))
        print("  Media URL:", d.get("media_url"))
        print("  Meta Media ID:", d.get("meta_media_id"))
        print("---")
        
    # Get latest failed message error
    res_msg = await db.fetch_all("SELECT * FROM messages WHERE status = 'failed' ORDER BY timestamp DESC LIMIT 3")
    for r in res_msg:
        d = dict(r)
        print("Message ID:", d.get("id"))
        print("  Phone:", d.get("phone"))
        print("  Status:", d.get("status"))
        print("  Error:", d.get("error_message"))
        print("  Row Data:", d.get("row_data"))
        print("---")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
