from fastapi import FastAPI, UploadFile, Form, Request, BackgroundTasks, File, staticfiles
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
load_dotenv()
from typing import Optional, List
import re
import os
import pandas as pd
import io
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import asyncio
import json
import random
import webbrowser
import requests
from contextlib import asynccontextmanager
from database import init_db, get_db
from utils import extract_phone_numbers, substitute_template, sync_to_google_sheet, send_email_report, get_now_utc, normalize_phone
from whatsapp_service import send_whatsapp_message, get_whatsapp_templates, create_whatsapp_template, create_whatsapp_otp_template, fetch_meta_templates, delete_whatsapp_template, upload_whatsapp_media, subscribe_waba_to_app
import datetime
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, PlainTextResponse
from auth_utils import hash_password, verify_password, create_session_token, verify_session_token
import httpx

import string
import secrets
import uuid
import time

# Settings
USE_REAL_API = True # Set to False for local testing without sending real messages


# Meta App Credentials (for Token Exchange)
FB_APP_ID = os.environ.get("FB_APP_ID", "916270141105838")
FB_APP_SECRET = os.environ.get("FB_APP_SECRET", "3f58694b5b0ec480d6992dabc16e6ece")
FB_CONFIG_ID = os.environ.get("FB_CONFIG_ID", "1819547065399749")
REGISTRATION_KEY = os.environ.get("REGISTRATION_KEY", "BITBINDERS_PRO_2024")

# --- System SMTP Configuration (Fixed Sender) ---
SYSTEM_EMAIL = os.environ.get('SYSTEM_EMAIL', 'devopsbitbinders@gmail.com')
SYSTEM_PASS = os.environ.get('SYSTEM_PASS', 'hzlx pcmv tpap yvbq')

# Webhook Verify Token
WEBHOOK_VERIFY_TOKEN = "Bitbinders_Secret_2013"

# --- Helper for JSON Serialization ---
def safe_json_response(data, status_code=200):
    try:
        json_str = json.dumps(data, default=str)
        return JSONResponse(content=json.loads(json_str), status_code=status_code)
    except Exception as e:
        print(f"DEBUG ERROR: Serialization failed: {str(e)}")
        return JSONResponse(content={"error": "Serialization failed"}, status_code=500)

async def get_user_id(username: str):
    db = await get_db()
    user = await db.fetch_one("SELECT id FROM users WHERE username = :u", {"u": username})
    return user['id'] if user else None

async def get_active_credentials(user_id: int):
    db = await get_db()
    row = await db.fetch_one("SELECT whatsapp_token, phone_number_id, waba_id FROM user_credentials WHERE is_active = 1 AND user_id = :u ORDER BY last_updated DESC LIMIT 1", {"u": user_id})
    if row:
        return dict(row)
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("DEBUG: Initializing database...")
        await init_db()
        print("DEBUG: Database initialized successfully.")
    except Exception as e:
        print(f"DEBUG: Error during database init: {str(e)}")
    
    # Start Campaign Scheduler
    scheduler_task = asyncio.create_task(campaign_scheduler())
        
    yield
    scheduler_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.post("/api/index")
@app.post("/api/whatsapp-link")
@app.post("/direct-whatsapp-link")
async def maximum_priority_auth(request: Request):
    return await facebook_auth_callback(request)

@app.get("/api/index")
@app.get("/api/whatsapp-link")
@app.get("/direct-whatsapp-link")
async def reachability_check():
    return {"status": "reachable", "handler": "active"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
event_queues = []

UPLOAD_DIR = "/tmp/uploads" if os.environ.get("VERCEL") else os.path.join(os.getcwd(), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return PlainTextResponse(
        content="User-agent: *\nAllow: /\nUser-agent: facebookexternalhit\nAllow: /",
        headers={"X-Robots-Tag": "index, follow, noarchive"}
    )

@app.post("/api/upload-media")
async def upload_media(request: Request, file: UploadFile = File(...)):
    try:
        session_token = request.cookies.get("session_token")
        username = verify_session_token(session_token)
        user_id = None
        if username:
            db = await get_db()
            u_row = await db.fetch_one("SELECT id FROM users WHERE username = :u", {"u": username})
            if u_row: user_id = u_row['id']

        ext = os.path.splitext(file.filename)[1]
        unique_id = uuid.uuid4().hex[:8]
        timestamp = int(time.time())
        unique_name = f"media_{timestamp}_{unique_id}{ext}"
        save_path = os.path.join(UPLOAD_DIR, unique_name)
        
        contents = await file.read()
        m_type = file.content_type
        if not m_type or m_type == "application/octet-stream":
            import mimetypes
            m_type = mimetypes.guess_type(file.filename)[0] or "image/png"
            
        with open(save_path, "wb") as buffer:
            buffer.write(contents)
            
        url = f"/static/uploads/{unique_name}"
        meta_id = None
        
        if user_id:
            try:
                creds = await get_active_credentials(user_id)
                if creds:
                    fb_id, upload_err = await upload_whatsapp_media(contents, file.filename, m_type, creds)
                    if fb_id:
                        meta_id = fb_id
                        print(f"DEBUG: Immediate Meta upload success for {username}: {meta_id}")
                    else:
                        print(f"DEBUG: Immediate Meta upload failed: {upload_err}")
            except Exception as e:
                print(f"DEBUG: Immediate Meta upload failed: {e}")

        return JSONResponse({"url": url, "meta_media_id": meta_id, "filename": file.filename})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/check")
async def check():
    return {"status": "ok", "version": "1.3", "routes": ["/auth/facebook/callback"]}

async def get_dashboard_stats(user_id: int):
    db = await get_db()
    ist_delta = datetime.timedelta(hours=5, minutes=30)
    now_ist = datetime.datetime.now(datetime.timezone(ist_delta))
    today_start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today_start_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    seven_days_ago_ist = today_start_ist - datetime.timedelta(days=7)
    seven_days_str = seven_days_ago_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    total_t = await db.fetch_one("SELECT COUNT(*) as count FROM templates WHERE user_id = :u", {"u": user_id})
    approved_t = await db.fetch_one("SELECT COUNT(*) as count FROM templates WHERE status = 'APPROVED' AND user_id = :u", {"u": user_id})
    inc_today = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE user_id = :u AND direction='inbound' AND timestamp >= :ts", {"u": user_id, "ts": today_str})
    inc_7d = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE user_id = :u AND direction='inbound' AND timestamp >= :ts", {"u": user_id, "ts": seven_days_str})
    camp_out_today = await db.fetch_one("SELECT COUNT(*) as count FROM messages WHERE user_id = :u AND timestamp >= :ts", {"u": user_id, "ts": today_str})
    camp_out_7d = await db.fetch_one("SELECT COUNT(*) as count FROM messages WHERE user_id = :u AND timestamp >= :ts", {"u": user_id, "ts": seven_days_str})
    
    return {
        "templates": {"total": total_t['count'] if total_t else 0, "approved": approved_t['count'] if approved_t else 0},
        "incoming": {"today": inc_today['count'] if inc_today else 0, "last_7_days": inc_7d['count'] if inc_7d else 0},
        "outgoing": {"today": camp_out_today['count'] or 0, "last_7_days": camp_out_7d['count'] or 0}
    }

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return RedirectResponse(url="/login", status_code=303)
        
    db = await get_db()
    u_id = await get_user_id(username)
    user_data = await db.fetch_one("SELECT is_admin, expiry_date, is_approved FROM users WHERE id = :u", {"u": u_id})
    is_admin = user_data['is_admin'] if user_data else 0
    
    if user_data and user_data['expiry_date']:
        now_str = get_now_utc()
        exp_val = user_data['expiry_date']
        exp_str = exp_val if isinstance(exp_val, str) else exp_val.strftime('%Y-%m-%d %H:%M:%S')
        if exp_str and now_str > exp_str:
            await db.execute("UPDATE users SET is_approved = 0 WHERE id = :u", {"u": u_id})
            return RedirectResponse(url="/login?error=expired", status_code=303)
    
    if user_data and not user_data['is_approved']:
        return RedirectResponse(url="/login?error=revoked", status_code=303)

    try:
        cred_row = await db.fetch_one("SELECT * FROM user_credentials WHERE user_id = :u AND is_active = 1 LIMIT 1", {"u": u_id})
        cred = dict(cred_row) if cred_row else None
        linked_phone = cred.get('phone_number') if cred else None
        waba_id = cred.get('waba_id') if cred else None
        phone_id = cred.get('phone_number_id') if cred else None
        access_token = cred.get('whatsapp_token') if cred else None

        campaigns = await db.fetch_all("SELECT * FROM campaigns WHERE user_id = :u ORDER BY timestamp DESC LIMIT 50", {"u": u_id})
        templates_raw = await db.fetch_all("SELECT * FROM templates WHERE user_id = :u ORDER BY name ASC", {"u": u_id})
        templates_list = []
        for row in templates_raw:
            t = dict(row)
            if t.get("components") and isinstance(t["components"], str):
                try: t["components"] = json.loads(t["components"])
                except: t["components"] = []
            templates_list.append(t)
                
        return templates.TemplateResponse(request=request, name="index.html", context={
            "request": request, "campaigns": campaigns, "templates": templates_list,
            "templates_json": json.dumps(templates_list, default=str),
            "fb_app_id": FB_APP_ID, "fb_config_id": FB_CONFIG_ID,
            "linked_phone": linked_phone, "waba_id": waba_id,
            "stats": await get_dashboard_stats(u_id), "username": username, "is_admin": is_admin
        })
    except Exception as e:
        print(f"DASHBOARD ERROR: {e}")
        return HTMLResponse(content=f"Dashboard Error: {str(e)}", status_code=500)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    session_token = request.cookies.get("session_token")
    if verify_session_token(session_token): return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html", context={"request": request})

@app.post("/api/auth/signup")
async def register(username: str = Form(...), business_name: str = Form(...), password: str = Form(...)):
    db = await get_db()
    existing = await db.fetch_one("SELECT id FROM users WHERE username = :u", {"u": username})
    if existing: return JSONResponse(status_code=400, content={"error": "Username exists"})
    pwd_hash, salt = hash_password(password)
    await db.execute("INSERT INTO users (username, business_name, password_hash, salt, is_approved, is_admin) VALUES (:u, :b, :p, :s, 0, 0)",
        {"u": username, "b": business_name, "p": pwd_hash, "s": salt})
    return {"message": "Account created! Waiting for approval."}

@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    db = await get_db()
    user = await db.fetch_one("SELECT * FROM users WHERE username = :u", {"u": username})
    if not user or not verify_password(password, user['salt'], user['password_hash']):
        return JSONResponse(status_code=401, content={"error": "Invalid login"})
    if not user['is_approved']:
        return JSONResponse(status_code=403, content={"error": "Account pending approval"})
    token = create_session_token(username)
    response = JSONResponse(content={"message": "Logged in", "redirect": "/"})
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=604800)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response

# --- Campaign Logic ---
async def process_campaign_batch(campaign_id: int, batch_size: int = 5):
    # Process a chunk of messages to avoid Vercel timeouts
    db = await get_db()
    try:
        # 1. Fetch Campaign Metadata
        raw_campaign = await db.fetch_one("SELECT * FROM campaigns WHERE id = :id", {"id": campaign_id})
        if not raw_campaign:
            return {"error": "Campaign not found", "completed": True}
        campaign = dict(raw_campaign)
        
        user_id = campaign.get('user_id')
        msg_type = campaign.get('msg_type')
        message_template = campaign.get('message_template')
        template_name = campaign.get('template_name')
        language_code = campaign.get('language_code')
        phone_col = campaign.get('phone_col')
        m_raw = campaign.get('mappings')
        mappings = json.loads(m_raw) if m_raw else None
        campaign_media_url = campaign.get('media_url')
        campaign_media_id = campaign.get('meta_media_id')
        
        # 2. Fetch pending messages
        pending_raw = await db.fetch_all(
            "SELECT * FROM messages WHERE campaign_id = :id AND status = 'pending' LIMIT :limit",
            {"id": campaign_id, "limit": batch_size}
        )
        pending_messages = [dict(m) for m in pending_raw]
        
        if not pending_messages:
            await db.execute("UPDATE campaigns SET status = 'Completed' WHERE id = :id", {"id": campaign_id})
            return {"completed": True, "processed": 0}

        # 3. Pre-fetch template
        template_def = None
        if msg_type == "template" and template_name:
            template_def = await db.fetch_one(
                "SELECT components FROM templates WHERE LOWER(name) = LOWER(:name) AND user_id = :u LIMIT 1", 
                {"name": template_name, "u": user_id}
            )

        # --- RE-UPLOAD TO META IF NEEDED (Ensures Phone ID Sync) ---
        credentials = await get_active_credentials(user_id)
        try:
            if (not campaign_media_id or campaign_media_id == "None") and campaign_media_url:
                full_url = str(campaign_media_url)
                if full_url and full_url.startswith("http"):
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        res = await client.get(full_url)
                        if res.status_code == 200:
                            fb_id, upload_err = await upload_whatsapp_media(res.content, "campaign_media", res.headers.get("Content-Type", "image/png"), credentials)
                            if fb_id:
                                campaign_media_id = fb_id
                                await db.execute("UPDATE campaigns SET meta_media_id = :mid WHERE id = :id", {"mid": campaign_media_id, "id": campaign_id})
        except Exception as e:
            print(f"DEBUG: Auto-upload to Meta exception: {e}")

        success_batch = 0
        failed_batch = 0

        for msg in pending_messages:
            phone = msg['phone']
            row = json.loads(msg['row_data']) if msg['row_data'] else {}
            media_url = campaign_media_url
            current_media_id = campaign_media_id
            message_to_send = ""
            forced_components = []

            if msg_type == "template":
                message_to_send = message_template or f"Template: {template_name}"
                comp_list = []
                if template_def and template_def['components']:
                    try: comp_list = json.loads(template_def['components'])
                    except: pass
                
                header_var_count = 0
                body_var_count = 0
                has_media_header = False
                media_header_type = 'image'
                
                if comp_list:
                    for c in comp_list:
                        ctype = str(c.get('type', '')).upper()
                        ctext = str(c.get('text', ''))
                        if ctype == 'HEADER':
                            header_var_count = len(re.findall(r'\{\{\s*\d+\s*\}\}', ctext))
                            if c.get('format') in ['IMAGE', 'VIDEO', 'DOCUMENT']:
                                has_media_header = True
                                media_header_type = str(c.get('format')).lower()
                        elif ctype == 'BODY':
                            body_var_count = len(re.findall(r'\{\{\s*\d+\s*\}\}', ctext))
                
                vars_map = mappings.get('vars', {}) if mappings else {}
                if not has_media_header and header_var_count > 0:
                    h_params = []
                    for i in range(1, header_var_count + 1):
                        m_val = vars_map.get(str(i))
                        h_params.append({"type": "text", "text": str(row.get(str(m_val).lower(), " "))})
                    forced_components.append({"type": "header", "parameters": h_params})

                if body_var_count > 0:
                    b_params = []
                    for i in range(1, body_var_count + 1):
                        mapping_key = str(i + header_var_count)
                        m_val = vars_map.get(mapping_key)
                        b_params.append({"type": "text", "text": str(row.get(str(m_val).lower(), " "))})
                    forced_components.append({"type": "body", "parameters": b_params})

                if has_media_header:
                    m_tag = media_header_type
                    if current_media_id:
                        forced_components.append({"type": "header", "parameters": [{"type": m_tag, m_tag: {"id": str(current_media_id)}}]})
                    elif str(media_url).startswith("http"):
                        forced_components.append({"type": "header", "parameters": [{"type": m_tag, m_tag: {"link": str(media_url)}}]})
            else:
                message_to_send = substitute_template(message_template or "", row)

            final_msg_type = msg_type
            if msg_type == "text" and media_url: final_msg_type = "image"

            success, response = await send_whatsapp_message(
                phone, message_to_send, final_msg_type, template_name, language_code, 
                media_url=None if msg_type == "template" else media_url, 
                credentials=credentials, forced_components=forced_components, media_id=current_media_id
            )

            wa_id = None
            err_msg = ""
            if success:
                success_batch += 1
                if isinstance(response, dict) and 'messages' in response: wa_id = response['messages'][0].get('id')
            else:
                failed_batch += 1
                err_msg = str(response)

            await db.execute(\"\"\"
                UPDATE messages SET status = :s, whatsapp_message_id = :mid, error_message = :err, message = :m
                WHERE id = :id
            \"\"\", {\"s\": 'sent' if success else 'failed', \"mid\": wa_id, \"err\": err_msg, \"m\": message_to_send, \"id\": msg['id']})
            await asyncio.sleep(0.5)

        await db.execute(\"\"\"
            UPDATE campaigns SET sent_success = sent_success + :s, sent_failed = sent_failed + :f,
                status = CASE WHEN (sent_success + sent_failed + :s + :f) >= total_numbers THEN 'Completed' ELSE 'Processing' END
            WHERE id = :id
        \"\"\", {\"s\": success_batch, \"f\": failed_batch, \"id\": campaign_id})
        
        progress_event = json.dumps({\"campaign_id\": campaign_id, \"success\": success_batch, \"failed\": failed_batch, \"total\": campaign['total_numbers']})
        for queue in event_queues: await queue.put(progress_event)

        return {\"completed\": False, \"processed\": len(pending_messages), \"success\": success_batch, \"failed\": failed_batch}
    except Exception as e:
        return {\"error\": str(e), \"completed\": False}

@app.post(\"/api/campaign/process-batch/{campaign_id}\")
async def process_batch_endpoint(campaign_id: int):
    return await process_campaign_batch(campaign_id)

@app.get(\"/events\")
async def events_handler(request: Request):
    queue = asyncio.Queue()
    event_queues.append(queue)
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected(): break
                data = await queue.get()
                yield f\"data: {data}\\n\\n\"
        except asyncio.CancelledError: pass
        finally: event_queues.remove(queue)
    return StreamingResponse(event_generator(), media_type=\"text/event-stream\")

@app.post(\"/api/get-columns\")
async def get_columns(file: UploadFile = File(...)):
    content = await file.read()
    df = pd.read_excel(io.BytesIO(content), nrows=1) if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(io.BytesIO(content), nrows=1)
    return {\"columns\": df.columns.tolist()}

@app.post(\"/api/campaign/create\")
async def create_campaign(request: Request, name: str = Form(...), template_name: str = Form(...), language_code: str = Form(...), phone_col: str = Form(...), mappings: str = Form(...), media_file: UploadFile = File(None)):
    session_token = request.cookies.get(\"session_token\")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={\"error\": \"Unauthorized\"})
    u_id = await get_user_id(username)
    db = await get_db()
    
    meta_media_id = None
    media_url = None
    if media_file and media_file.filename:
        m_content = await media_file.read()
        unique_name = f\"media_{int(time.time())}_{media_file.filename}\"
        save_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(save_path, \"wb\") as f: f.write(m_content)
        media_url = f\"/static/uploads/{unique_name}\"
        creds = await get_active_credentials(u_id)
        if creds:
            fb_id, _ = await upload_whatsapp_media(m_content, media_file.filename, media_file.content_type, creds)
            meta_media_id = fb_id

    # Create Campaign
    query = \"\"\"INSERT INTO campaigns (user_id, name, total_numbers, status, message_template, msg_type, template_name, language_code, mappings, phone_col, media_url, meta_media_id)
               VALUES (:u, :n, 0, 'Pending', '', 'template', :tn, :l, :m, :p, :mu, :mid)\"\"\"
    campaign_id = await db.execute(query, {\"u\": u_id, \"n\": name, \"tn\": template_name, \"l\": language_code, \"m\": mappings, \"p\": phone_col, \"mu\": media_url, \"mid\": meta_media_id})
    return {\"campaign_id\": campaign_id}

@app.post(\"/api/campaign/add-numbers/{campaign_id}\")
async def add_numbers(campaign_id: int, request: Request):
    data = await request.json()
    numbers = data.get(\"numbers\", [])
    db = await get_db()
    for row in numbers:
        await db.execute(\"INSERT INTO messages (campaign_id, phone, status, row_data) VALUES (:c, :p, 'pending', :r)\",
            {\"c\": campaign_id, \"p\": row.get('phone'), \"r\": json.dumps(row)})
    await db.execute(\"UPDATE campaigns SET total_numbers = total_numbers + :n WHERE id = :id\", {\"n\": len(numbers), \"id\": campaign_id})
    return {\"message\": \"Numbers added\"}

# --- Background Task Placeholder ---
async def campaign_scheduler():
    while True:
        await asyncio.sleep(60)

if __name__ == \"__main__\":
    import uvicorn
    uvicorn.run(app, host=\"0.0.0.0\", port=8000)
