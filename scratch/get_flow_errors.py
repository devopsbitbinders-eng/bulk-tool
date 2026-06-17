import asyncio
import httpx
from database import get_db

async def get_flow_validation_errors():
    db = await get_db()
    creds = await db.fetch_one("SELECT whatsapp_token, waba_id FROM user_credentials WHERE user_id = 12 LIMIT 1")
    if not creds:
        print("No active credentials found in DB.")
        return
        
    waba_id = creds['waba_id']
    access_token = creds['whatsapp_token']

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # We will fetch the most recently created flow for this WABA to check its validation errors
    url_flows = f"https://graph.facebook.com/v21.0/{waba_id}/flows"
    async with httpx.AsyncClient() as client:
        res = await client.get(url_flows, headers=headers)
        if res.status_code == 200:
            flows = res.json().get('data', [])
            if flows:
                latest_flow = flows[0]['id']
                # Now fetch validation errors for this flow
                url_err = f"https://graph.facebook.com/v21.0/{latest_flow}?fields=validation_errors,name"
                res_err = await client.get(url_err, headers=headers)
                print("--- VALIDATION ERRORS FOR LATEST FLOW ---")
                import json
                print(json.dumps(res_err.json(), indent=2))
            else:
                print("No flows found.")
        else:
            print("Failed to fetch flows", res.text)

if __name__ == "__main__":
    asyncio.run(get_flow_validation_errors())
