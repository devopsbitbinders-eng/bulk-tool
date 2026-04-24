import asyncio
import os
import requests
from dotenv import load_dotenv
load_dotenv()

from database import get_db
from whatsapp_service import subscribe_waba_to_app

async def force_subscribe_all():
    db = await get_db()
    rows = await db.fetch_all("SELECT waba_id, whatsapp_token, user_id FROM user_credentials WHERE is_active = 1")
    print(f"Found {len(rows)} active accounts to subscribe.")
    
    for r in rows:
        waba_id = r['waba_id']
        token = r['whatsapp_token']
        u_id = r['user_id']
        
        print(f"Subscribing User {u_id} (WABA: {waba_id})...")
        success = await subscribe_waba_to_app(waba_id, token)
        if success:
            print(f"Successfully subscribed WABA {waba_id}")
        else:
            print(f"Failed to subscribe WABA {waba_id}")

if __name__ == "__main__":
    asyncio.run(force_subscribe_all())
