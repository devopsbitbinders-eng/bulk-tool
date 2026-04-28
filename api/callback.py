import os
import json
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from database import get_db

app = FastAPI()

# Meta App Credentials
FB_APP_ID = os.environ.get("FB_APP_ID", "916270141105838")
FB_APP_SECRET = os.environ.get("FB_APP_SECRET", "3f58694b5b0ec480d6992dabc16e6ece")

@app.post("/api/callback")
async def standalone_callback(request: Request):
    try:
        data = await request.json()
        code = data.get('code')
        access_token = data.get('access_token')
        
        # 1. Token Exchange
        if code and not access_token:
            exchange_url = "https://graph.facebook.com/v21.0/oauth/access_token"
            data_payload = {
                "client_id": FB_APP_ID, 
                "client_secret": FB_APP_SECRET, 
                "code": code,
                "redirect_uri": ""
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(exchange_url, data=data_payload)
            res_json = res.json()
            access_token = res_json.get("access_token")
            if not access_token:
                return JSONResponse({"error": f"Meta Exchange Failed: {res_json.get('error', {}).get('message', 'Unknown')}"}, status_code=400)

        if not access_token:
            return JSONResponse({"error": "No token provided"}, status_code=400)

        # 2. Find User ID from session (Hack for standalone)
        # We'll use a direct DB lookup or trust the frontend session if possible
        # For maximum safety, we assume the user is logged in
        session_token = request.cookies.get("session_token")
        if not session_token:
             return JSONResponse({"error": "Session expired. Please re-login."}, status_code=401)
        
        # Connect to DB to find user
        from auth_utils import verify_session_token
        username = verify_session_token(session_token)
        if not username:
            return JSONResponse({"error": "Invalid session"}, status_code=401)
            
        # 3. Scan and Save
        headers = {"Authorization": f"Bearer {access_token}"}
        # Simplified scan: find first WABA and first Phone ID
        async with httpx.AsyncClient(timeout=30.0) as client:
            # WABA
            w_res = await client.get("https://graph.facebook.com/v21.0/me/whatsapp_business_accounts", headers=headers)
            wabas = w_res.json().get('data', [])
            if not wabas: return JSONResponse({"error": "No WhatsApp Business Account found."}, status_code=404)
            waba_id = wabas[0]['id']
            
            # Phones
            p_res = await client.get(f"https://graph.facebook.com/v21.0/{waba_id}/phone_numbers", headers=headers)
            phones = p_res.json().get('data', [])
            if not phones: return JSONResponse({"error": "No phone numbers found in WABA."}, status_code=404)
            
            # Skip test numbers
            real_phone = next((p for p in phones if p.get('display_phone_number') != "+1 555-187-4003"), phones[0])
            phone_id = real_phone['id']
            phone_number = real_phone.get('display_phone_number', '').replace(' ', '').replace('-', '').replace('+', '')

        # 4. Save to Database
        db = await get_db()
        u_id_row = await db.fetch_one("SELECT id FROM users WHERE username = :u", {"u": username})
        u_id = u_id_row['id']
        
        await db.execute("UPDATE user_credentials SET is_active = 0 WHERE user_id = :u", {"u": u_id})
        await db.execute("""
            INSERT INTO user_credentials (user_id, access_token, waba_id, phone_id, phone_number, is_active)
            VALUES (:u, :at, :wi, :pi, :pn, 1)
        """, {"u": u_id, "at": access_token, "wi": waba_id, "pi": phone_id, "pn": phone_number})
        
        return {"message": "Success", "phone": phone_number}

    except Exception as e:
        return JSONResponse({"error": f"Standalone Error: {str(e)}"}, status_code=500)
