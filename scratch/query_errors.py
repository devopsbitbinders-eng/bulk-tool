import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from database import db

async def main():
    await db.connect()
    res = await db.fetch_all("SELECT c.id, c.media_url, c.meta_media_id, m.id as msg_id, m.error_message, m.timestamp FROM messages m JOIN campaigns c ON m.campaign_id = c.id WHERE m.status = 'failed' AND m.error_message LIKE '%Media%' ORDER BY m.timestamp DESC LIMIT 1")
    print([dict(r) for r in res])
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
