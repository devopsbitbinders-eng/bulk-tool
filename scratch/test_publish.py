import asyncio
from database import get_db
import json
import httpx
from flow_api_utils import create_and_publish_meta_flow

async def main():
    db = await get_db()
    user = await db.fetch_one("SELECT id FROM users LIMIT 1")
    if not user:
        print("No user")
        return
    u_id = user['id']
    creds = await db.fetch_one("SELECT whatsapp_token, waba_id FROM user_credentials WHERE is_active = 1 AND user_id = :u LIMIT 1", {"u": u_id})
    if not creds:
        print("No creds")
        return
        
    questions = [
        {"format": "TEXT", "text": "What is your name?"},
        {"format": "NUMBER", "text": "Age?"}
    ]
    try:
        flow_id = await create_and_publish_meta_flow(creds['waba_id'], creds['whatsapp_token'], "Test Flow Publish", questions)
        print("Success:", flow_id)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
