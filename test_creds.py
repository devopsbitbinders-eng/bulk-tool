import asyncio
from database import get_db

async def run():
    db = await get_db()
    row = await db.fetch_one("SELECT * FROM user_credentials LIMIT 1")
    if row:
        print("CREDENTIALS FOUND in MySQL:")
        print(f"Token (First 15 chars): {row['whatsapp_token'][:15]}...")
        print(f"Phone Number ID: {row['phone_number_id']}")
        print(f"WABA ID: {row['waba_id']}")
    else:
        print("NO CREDENTIALS FOUND")

asyncio.run(run())
