import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from database import get_db

async def check_creds():
    db = await get_db()
    rows = await db.fetch_all("SELECT user_id, phone_number_id, whatsapp_token FROM user_credentials")
    print("USER CREDENTIALS:")
    for r in rows:
        print(f"User: {r['user_id']}, PhoneID: {r['phone_number_id']}, Token: {r['whatsapp_token'][:10]}...")

if __name__ == "__main__":
    asyncio.run(check_creds())
