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
        provided_waba = data.get('waba_id')
        provided_phone = data.get('phone_id')
        
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

        # 2. Get User
        session_token = request.cookies.get("session_token")
        if not session_token: return JSONResponse({"error": "Session expired"}, status_code=401)
        from auth_utils import verify_session_token
        username = verify_session_token(session_token)
        if not username: return JSONResponse({"error": "Invalid session"}, status_code=401)
        
        db = await get_db()
        u_row = await db.fetch_one("SELECT id FROM users WHERE username = :u", {"u": username})
        u_id = u_row['id']

        # 3. Handle WABA/Phone ID (Trust frontend first)
        headers = {"Authorization": f"Bearer {access_token}"}
        waba_id = provided_waba if provided_waba and provided_waba != 'AUTO_DETECT' else None
        phone_id = provided_phone if provided_phone and provided_phone != 'AUTO_DETECT' else None
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if not waba_id:
                # Scan fallback
                w_res = await client.get("https://graph.facebook.com/v21.0/me?fields=whatsapp_business_accounts{id,name}", headers=headers)
                w_data = w_res.json().get('whatsapp_business_accounts', {}).get('data', [])
                if w_data:
                    waba_id = next((w['id'] for w in w_data if "test" not in w.get('name', '').lower()), w_data[0]['id'])
            
            if not waba_id: return JSONResponse({"error": "Meta: No WhatsApp Business Account found."}, status_code=404)
            
            if not phone_id:
                p_res = await client.get(f"https://graph.facebook.com/v21.0/{waba_id}/phone_numbers", headers=headers)
                p_data = p_res.json().get('data', [])
                if p_data:
                    best_p = next((p for p in p_data if p.get('display_phone_number') != "+1 555-187-4003"), p_data[0])
                    phone_id = best_p['id']
                    phone_number = best_p.get('display_phone_number', '').replace(' ', '').replace('-', '').replace('+', '')
                else:
                    return JSONResponse({"error": "No phone numbers found in WABA"}, status_code=404)
            else:
                # Fetch phone number text
                p_res = await client.get(f"https://graph.facebook.com/v21.0/{phone_id}", headers=headers)
                phone_number = p_res.json().get('display_phone_number', 'Linked').replace(' ', '').replace('-', '').replace('+', '')

        # 4. Save
        await db.execute("UPDATE user_credentials SET is_active = 0 WHERE user_id = :u", {"u": u_id})
        await db.execute("""
            INSERT INTO user_credentials (user_id, whatsapp_token, phone_number_id, waba_id, phone_number, is_active)
            VALUES (:u, :at, :pi, :wi, :pn, 1)
        """, {"u": u_id, "at": access_token, "pi": phone_id, "wi": waba_id, "pn": phone_number})
        
        from whatsapp_service import subscribe_waba_to_app
        await subscribe_waba_to_app(waba_id, access_token)
        
        return {"message": "Success", "phone": phone_number}

    except Exception as e:
        return JSONResponse({"error": f"API Error: {str(e)}"}, status_code=500)

    except Exception as e:
        return JSONResponse({"error": f"Standalone Error: {str(e)}"}, status_code=500)
