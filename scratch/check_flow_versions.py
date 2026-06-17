import asyncio
import httpx
from database import get_db

async def get_exact_flow_versions():
    db = await get_db()
    creds = await db.fetch_one("SELECT whatsapp_token, waba_id FROM user_credentials WHERE is_active = 1 LIMIT 1")
    if not creds:
        print("No active credentials found in DB.")
        return
        
    waba_id = creds['waba_id']
    access_token = creds['whatsapp_token']

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"https://graph.facebook.com/v21.0/{waba_id}/flows_controlled_features"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("--- ALLOWED META FLOW VERSIONS & FEATURES ---")
            import pprint
            pprint.pprint(data)
        else:
            print(f"Error fetching versions: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(get_exact_flow_versions())
