import asyncio
from database import get_db
import requests

async def run():
    db = await get_db()
    row = await db.fetch_one("SELECT * FROM user_credentials LIMIT 1")
    if not row:
        print("No creds")
        return

    url = f"https://graph.facebook.com/v21.0/{row['waba_id']}/message_templates"
    headers = {"Authorization": f"Bearer {row['whatsapp_token']}"}
    
    print("Fetching from:", url)
    resp = requests.get(url, headers=headers)
    print("Status Code:", resp.status_code)
    try:
        data = resp.json()
        print("JSON length of 'data':", len(data.get('data', [])))
        if len(data.get('data', [])) == 0:
            print("Full JSON Payload:", data)
    except Exception as e:
        print("Error parsing JSON:", str(e))

asyncio.run(run())
