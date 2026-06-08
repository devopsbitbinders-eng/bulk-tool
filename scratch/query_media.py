import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from database import db
import httpx

async def main():
    await db.connect()
    # User 12 from previous webhook logs
    creds = await db.fetch_one("SELECT whatsapp_token FROM users WHERE id = 12")
    if creds and creds['whatsapp_token']:
        token = creds['whatsapp_token']
        media_id = '840978585240192'
        url = f"https://graph.facebook.com/v19.0/{media_id}"
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            print("Media Info:", resp.status_code, resp.text)
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
