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
# The user should configure these in their Meta App Dashboard
FB_APP_ID = "916270141105838" 
FB_APP_SECRET = "3f58694b5b0ec480d6992dabc16e6ece"
FB_CONFIG_ID = "2015666162711485" # Configuration ID for Business Login
REGISTRATION_KEY = os.environ.get("REGISTRATION_KEY", "BITBINDERS_PRO_2024")
# Admin Key system removed for maximum security. Use promote_admin.py instead.

# --- System SMTP Configuration (Fixed Sender) ---
SYSTEM_EMAIL = os.environ.get('SYSTEM_EMAIL', 'devopsbitbinders@gmail.com')
SYSTEM_PASS = os.environ.get('SYSTEM_PASS', 'hzlx pcmv tpap yvbq') # Set this in environment
# -----------------------------------------------

# Webhook Verify Token (User should paste this in Meta Dashboard)
WEBHOOK_VERIFY_TOKEN = "Bitbinders_Secret_2013"

# --- Helper for JSON Serialization (MySQL Datetime fix) ---
def safe_json_response(data, status_code=200):
    try:
        # We use json.dumps with default=str to convert datetimes/decimals to strings
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
    # First, try to find active credentials
    row = await db.fetch_one("SELECT whatsapp_token as token, phone_number_id as phone_id, waba_id FROM user_credentials WHERE is_active = 1 AND user_id = :u ORDER BY last_updated DESC LIMIT 1", {"u": user_id})
    if row:
        return dict(row)
    
    # Fallback: Check if any credentials exist at all (maybe inactive?)
    any_creds = await db.fetch_one("SELECT id FROM user_credentials WHERE user_id = :u LIMIT 1", {"u": user_id})
    if any_creds:
        print(f"DEBUG: User {user_id} has credentials but NONE ARE ACTIVE.")
    else:
        print(f"DEBUG: User {user_id} has NO credentials in the database.")
        
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        print("DEBUG: Initializing database...")
        await init_db()
        print("DEBUG: Database initialized successfully.")
    except Exception as e:
        print(f"DEBUG: Error during database init: {str(e)}")
    
    # Start Campaign Scheduler
    scheduler_task = asyncio.create_task(campaign_scheduler())
        
    yield
    # Shutdown logic
    scheduler_task.cancel()

app = FastAPI(lifespan=lifespan)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
event_queues = []

# Media Upload Directory — use /tmp on Vercel (read-only filesystem), fallback to static/uploads locally
UPLOAD_DIR = "/tmp/uploads" if os.environ.get("VERCEL") else os.path.join(os.getcwd(), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# SPECIFIC MOUNT FOR UPLOADS (High Priority)
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads_mount")
# General static mount
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/robots.txt", response_class=PlainTextResponse)
@app.head("/robots.txt")
async def robots_txt():
    return PlainTextResponse(
        content="User-agent: *\nAllow: /\nUser-agent: facebookexternalhit\nAllow: /",
        headers={"X-Robots-Tag": "index, follow, noarchive"}
    )

@app.post("/api/upload-media")
async def upload_media(file: UploadFile = File(...)):
    try:
        ext = os.path.splitext(file.filename)[1]
        unique_id = uuid.uuid4().hex[:8]
        timestamp = int(time.time())
        unique_name = f"media_{timestamp}_{unique_id}{ext}"
        save_path = os.path.join(UPLOAD_DIR, unique_name)
        
        with open(save_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        url = f"/static/uploads/{unique_name}"
        print(f"DEBUG: File uploaded to {save_path}, URL: {url}")
        return {"url": url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/check")
async def check():
    return {"status": "ok", "version": "1.2", "routes": ["/auth/facebook/callback"]}

# Dummy routes to clean up 404 noise from old browser tabs
@app.get("/campaign/stats")
async def campaign_stats():
    return {"success": 0, "failed": 0, "total": 0}

@app.get("/report")
async def report():
    return {"message": "No report available"}

async def get_dashboard_stats(user_id: int):
    db = await get_db()
    
    ist_delta = datetime.timedelta(hours=5, minutes=30)
    now_ist = datetime.datetime.now(datetime.timezone(ist_delta))
    today_start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today_start_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    seven_days_ago_ist = today_start_ist - datetime.timedelta(days=7)
    seven_days_str = seven_days_ago_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    # Total Templates & Approved
    total_t = await db.fetch_one("SELECT COUNT(*) as count FROM templates WHERE user_id = :u", {"u": user_id})
    approved_t = await db.fetch_one("SELECT COUNT(*) as count FROM templates WHERE status = 'APPROVED' AND user_id = :u", {"u": user_id})

    # Incoming
    inc_today = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE user_id = :u AND direction='inbound' AND timestamp >= :ts", {"u": user_id, "ts": today_str})
    inc_7d = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE user_id = :u AND direction='inbound' AND timestamp >= :ts", {"u": user_id, "ts": seven_days_str})

    # Outgoing
    camp_out_today = await db.fetch_one("SELECT COUNT(*) as count FROM messages WHERE user_id = :u AND timestamp >= :ts", {"u": user_id, "ts": today_str})
    camp_out_7d = await db.fetch_one("SELECT COUNT(*) as count FROM messages WHERE user_id = :u AND timestamp >= :ts", {"u": user_id, "ts": seven_days_str})
    
    return {
        "templates": {
            "total": total_t['count'] if total_t else 0,
            "approved": approved_t['count'] if approved_t else 0
        },
        "incoming": {
            "today": inc_today['count'] if inc_today else 0,
            "last_7_days": inc_7d['count'] if inc_7d else 0
        },
        "outgoing": {
            "today": camp_out_today['count'] or 0,
            "last_7_days": camp_out_7d['count'] or 0
        }
    }

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Check for authentication
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username:
        return RedirectResponse(url="/login", status_code=303)
        
    db = await get_db()
    u_id = await get_user_id(username)
    
    # Get linked account info specifically for this user
    user_data = await db.fetch_one("SELECT is_admin, expiry_date, is_approved FROM users WHERE id = :u", {"u": u_id})
    is_admin = user_data['is_admin'] if user_data else 0
    
    # NEW: Check for auto-revocation on load
    if user_data and user_data['expiry_date']:
        now_str = get_now_utc()
        exp_val = user_data['expiry_date']
        # Convert to string if it's a datetime object (MySQL)
        exp_str = exp_val if isinstance(exp_val, str) else exp_val.strftime('%Y-%m-%d %H:%M:%S')
            
        if exp_str and now_str > exp_str:
            await db.execute("UPDATE users SET is_approved = 0 WHERE id = :u", {"u": u_id})
            return RedirectResponse(url="/login?error=expired", status_code=303)
    
    if user_data and not user_data['is_approved']:
        return RedirectResponse(url="/login?error=revoked", status_code=303)

    cred = await db.fetch_one("SELECT phone_number, waba_id FROM user_credentials WHERE is_active = 1 AND user_id = :u LIMIT 1", {"u": u_id})
    linked_phone = cred['phone_number'] if cred else None
    waba_id = cred['waba_id'] if cred else None

    campaigns = await db.fetch_all("SELECT * FROM campaigns WHERE user_id = :u ORDER BY timestamp DESC LIMIT 50", {"u": u_id})
    
    templates_raw = await db.fetch_all("SELECT * FROM templates WHERE user_id = :u ORDER BY name ASC", {"u": u_id})
    templates_list = []
    for row in templates_raw:
        t = dict(row)
        # Pre-parse JSON for template safety
        if t.get("components") and isinstance(t["components"], str):
            try: t["components"] = json.loads(t["components"])
            except: t["components"] = []
        if t.get("variable_map") and isinstance(t["variable_map"], str):
            try: t["variable_map"] = json.loads(t["variable_map"])
            except: t["variable_map"] = {}
        templates_list.append(t)
            
    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request, 
        "campaigns": campaigns,
        "templates": templates_list,
        "templates_json": json.dumps(templates_list, default=str),
        "fb_app_id": FB_APP_ID,
        "fb_config_id": FB_CONFIG_ID,
        "linked_phone": linked_phone,
        "waba_id": waba_id,
        "stats": await get_dashboard_stats(u_id),
        "username": username,
        "is_admin": is_admin
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # If already logged in, go to dashboard
    session_token = request.cookies.get("session_token")
    if verify_session_token(session_token):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html", context={"request": request})

@app.get("/privacy", response_class=HTMLResponse)
@app.head("/privacy")
async def privacy_page(request: Request):
    response = templates.TemplateResponse(request=request, name="privacy.html", context={"request": request})
    response.headers["X-Robots-Tag"] = "index, follow, noarchive"
    return response


@app.post("/api/auth/signup")
async def register(username: str = Form(...), business_name: str = Form(...), password: str = Form(...)):
    db = await get_db()
    
    # Default is a regular, unapproved user.
    # To make someone an admin, run the promote_admin.py script.
    is_admin = 0
    is_approved = 0

    # Check if user exists
    existing = await db.fetch_one("SELECT id FROM users WHERE username = :u", {"u": username})
    if existing:
        return JSONResponse(status_code=400, content={"error": "Username already exists"})
    
    pwd_hash, salt = hash_password(password)
    await db.execute(
        "INSERT INTO users (username, business_name, password_hash, salt, is_approved, is_admin) VALUES (:u, :b, :p, :s, :a, :adm)",
        {"u": username, "b": business_name, "p": pwd_hash, "s": salt, "a": is_approved, "adm": is_admin}
    )
    
    msg = "Account created successfully! Admin will approve your login shortly."
    if is_admin:
        msg = "Admin account created! You can now log in."
        
    return {"message": msg}

@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    try:
        db = await get_db()
        user = await db.fetch_one("SELECT * FROM users WHERE username = :u", {"u": username})
        
        if not user:
            return JSONResponse(status_code=401, content={"error": "Invalid username or password"})
        
        # Check password with correct hash/salt order (password, salt, hash)
        is_valid = verify_password(password, user['salt'], user['password_hash'])
        if not is_valid:
            return JSONResponse(status_code=401, content={"error": "Invalid username or password"})
        
        # Safe check for is_approved column
        is_approved = 1
        if 'is_approved' in user.keys():
            is_approved = user['is_approved']
        
        if not is_approved:
            return JSONResponse(status_code=403, content={"error": "Your account is pending administrator approval or has been revoked."})
        
        # Check Expiry
        if user['expiry_date']:
            now_str = get_now_utc()
            exp_val = user['expiry_date']
            exp_str = exp_val if isinstance(exp_val, str) else exp_val.strftime('%Y-%m-%d %H:%M:%S')
            
            if exp_str and now_str > exp_str:
                await db.execute("UPDATE users SET is_approved = 0 WHERE id = :u", {"u": user['id']})
                return JSONResponse(status_code=403, content={"error": "Your access has expired. Please contact the administrator."})
        
        token = create_session_token(username)
        response = JSONResponse(content={"message": "Logged in successfully", "redirect": "/"})
        response.set_cookie(key="session_token", value=token, httponly=True, max_age=604800) # 7 days
        return response
    except Exception as e:
        print(f"CRITICAL LOGIN ERROR: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Database Error: {str(e)}"})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response

# --- Admin API ---
@app.get("/api/admin/users")
async def admin_get_users(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    db = await get_db()
    admin_check = await db.fetch_one("SELECT is_admin FROM users WHERE username = :u", {"u": username})
    if not admin_check or not admin_check['is_admin']:
        return JSONResponse(status_code=403, content={"error": "Access Denied"})
    
    users = await db.fetch_all("SELECT id, username, business_name, is_approved, is_admin, expiry_date, created_at FROM users WHERE is_admin = 0 ORDER BY created_at DESC")
    return [dict(u) for u in users]


@app.post("/api/admin/approve/{user_id}")
async def admin_approve_user(user_id: int, request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    db = await get_db()
    admin_check = await db.fetch_one("SELECT is_admin FROM users WHERE username = :u", {"u": username})
    if not admin_check or not admin_check['is_admin']:
        return JSONResponse(status_code=403, content={"error": "Access Denied"})
    
    await db.execute("UPDATE users SET is_approved = 1 WHERE id = :id", {"id": user_id})
    return {"message": "User approved successfully"}

@app.post("/api/admin/revoke/{user_id}")
async def admin_revoke_user(user_id: int, request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    db = await get_db()
    admin_check = await db.fetch_one("SELECT is_admin FROM users WHERE username = :u", {"u": username})
    if not admin_check or not admin_check['is_admin']:
        return JSONResponse(status_code=403, content={"error": "Access Denied"})
    
    await db.execute("UPDATE users SET is_approved = 0 WHERE id = :id", {"id": user_id})
    return {"message": "User access revoked"}

@app.post("/api/admin/set-expiry/{user_id}")
async def admin_set_expiry(user_id: int, request: Request, expiry: str = Form(...)):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    db = await get_db()
    admin_check = await db.fetch_one("SELECT is_admin FROM users WHERE username = :u", {"u": username})
    if not admin_check or not admin_check['is_admin']:
        return JSONResponse(status_code=403, content={"error": "Access Denied"})
    
    # Format expected: YYYY-MM-DD
    # We'll store it as end of that day in UTC
    expiry_dt = f"{expiry} 23:59:59"
    await db.execute("UPDATE users SET expiry_date = :exp WHERE id = :id", {"exp": expiry_dt, "id": user_id})
    return {"message": f"Expiry date set to {expiry}"}

@app.post("/api/admin/delete/{user_id}")
async def admin_delete_user(user_id: int, request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    db = await get_db()
    admin_check = await db.fetch_one("SELECT is_admin FROM users WHERE username = :u", {"u": username})
    if not admin_check or not admin_check['is_admin']:
        return JSONResponse(status_code=403, content={"error": "Access Denied"})
    
    # Don't delete yourself
    me = await db.fetch_one("SELECT id FROM users WHERE username = :u", {"u": username})
    if me and me['id'] == user_id:
        return JSONResponse(status_code=400, content={"error": "You cannot delete your own account"})

    await db.execute("DELETE FROM users WHERE id = :id", {"id": user_id})
    return {"message": "User deleted successfully"}

@app.get("/api/templates")
async def api_get_templates(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    templates_raw = await db.fetch_all("SELECT * FROM templates WHERE user_id = :u ORDER BY name ASC", {"u": u_id})
    templates_list = []
    for row in templates_raw:
        t = dict(row)
        if t.get("components") and isinstance(t["components"], str):
            try: t["components"] = json.loads(t["components"])
            except: t["components"] = []
        if t.get("variable_map") and isinstance(t["variable_map"], str):
            try: t["variable_map"] = json.loads(t["variable_map"])
            except: t["variable_map"] = {}
        templates_list.append(t)
    return templates_list

async def process_campaign_batch(campaign_id: int, batch_size: int = 5):
    """Processes a small batch of pending messages for a campaign. Prevents timeouts."""
    try:
        db = await get_db()
    
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
        
        # 2. Fetch pending messages
        pending_raw = await db.fetch_all(
            "SELECT * FROM messages WHERE campaign_id = :id AND status = 'pending' LIMIT :limit",
            {"id": campaign_id, "limit": batch_size}
        )
        pending_messages = [dict(m) for m in pending_raw]
        
        if not pending_messages:
            await db.execute("UPDATE campaigns SET status = 'Completed' WHERE id = :id", {"id": campaign_id})
            return {"completed": True, "processed": 0}

        # 3. Pre-fetch template for Smart Distribution
        template_def = None
        if msg_type == "template" and template_name:
            template_def = await db.fetch_one(
                "SELECT components FROM templates WHERE LOWER(name) = LOWER(:name) AND user_id = :u LIMIT 1", 
                {"name": template_name, "u": user_id}
            )

        processed_count = 0
        success_batch = 0
        failed_batch = 0

        for msg in pending_messages:
            phone = msg['phone']
            row = json.loads(msg['row_data']) if msg['row_data'] else {}
            
            media_url = campaign_media_url
            message_to_send = ""
            forced_components = []

            if msg_type == "template":
                message_to_send = message_template or f"Template: {template_name}"
                header_params = []
                body_params = []
                
                comp_list = []
                if template_def and template_def['components']:
                    try: comp_list = json.loads(template_def['components'])
                    except: pass
                
                header_var_count = 0
                body_var_count = 0
                has_media_header = False
                
                if comp_list:
                    for c in comp_list:
                        ctype = str(c.get('type', '')).upper()
                        ctext = str(c.get('text', ''))
                        if ctype == 'HEADER':
                            header_var_count = len(re.findall(r'\{\{\s*\d+\s*\}\}', ctext))
                            if c.get('format') in ['IMAGE', 'VIDEO', 'DOCUMENT']:
                                has_media_header = True
                        elif ctype == 'BODY':
                            body_var_count = len(re.findall(r'\{\{\s*\d+\s*\}\}', ctext))
                
                if mappings:
                    vars_map = mappings.get('vars', {})
                    sorted_keys = sorted(vars_map.keys(), key=lambda x: int(x))
                    for idx, k in enumerate(sorted_keys):
                        val = str(row.get(vars_map[k], "")).strip()
                        if not val: val = " "
                        
                        if idx < header_var_count:
                            header_params.append({"type": "text", "text": val})
                        else:
                            body_params.append({"type": "text", "text": val})
                        
                        pattern = r'\{\{\s*' + re.escape(str(idx + 1)) + r'\s*\}\}'
                        message_to_send = re.sub(pattern, val, message_to_send, flags=re.IGNORECASE)
                    
                    if mappings.get('header'):
                        media_url = row.get(mappings['header'])

                # Build Components
                if has_media_header and media_url:
                    fmt = "image"
                    if str(media_url).lower().endswith((".mp4", ".mov")): fmt = "video"
                    elif str(media_url).lower().endswith((".pdf", ".doc", ".docx")): fmt = "document"
                    forced_components.append({
                        "type": "header",
                        "parameters": [{"type": fmt, fmt: {"link": media_url}}]
                    })
                elif header_params:
                    forced_components.append({"type": "header", "parameters": header_params})
                
                if body_params:
                    forced_components.append({"type": "body", "parameters": body_params})
                
                # Final Safety Padding
                if header_var_count > 0 and not header_params:
                     forced_components.append({"type": "header", "parameters": [{"type": "text", "text": " "}]})
                if body_var_count > 0 and not body_params:
                     forced_components.append({"type": "body", "parameters": [{"type": "text", "text": " "}]})
            else:
                message_to_send = substitute_template(message_template or "", row)

            # Auto-detect msg_type if it's text but we have a media_url
            final_msg_type = msg_type
            if msg_type == "text" and media_url:
                final_msg_type = "image"
                if str(media_url).lower().endswith((".mp4", ".mov")): final_msg_type = "video"
                elif str(media_url).lower().endswith((".pdf", ".doc", ".docx", ".xlsx", ".xls")): final_msg_type = "document"

            # Send Message
            credentials = await get_active_credentials(user_id)
            success, response = await send_whatsapp_message(
                phone, message_to_send, final_msg_type, template_name, language_code, 
                media_url=media_url, credentials=credentials, forced_components=forced_components
            )

            wa_message_id = None
            error_msg = ""
            if success:
                success_batch += 1
                if isinstance(response, dict) and 'messages' in response:
                    wa_message_id = response['messages'][0].get('id')
            else:
                failed_batch += 1
                error_msg = str(response)[:500]

            # Update Message Record
            await db.execute("""
                UPDATE messages SET status = :s, whatsapp_message_id = :mid, error_message = :err, message = :m
                WHERE id = :id
            """, {"s": 'sent' if success else 'failed', "mid": wa_message_id, "err": error_msg, "m": message_to_send, "id": msg['id']})
            
            processed_count += 1
            # Small delay between messages in batch
            await asyncio.sleep(2)

        # 4. Update Campaign Totals
        total_processed = campaign['sent_success'] + campaign['sent_failed'] + processed_count
        await db.execute("""
            UPDATE campaigns 
            SET sent_success = sent_success + :s, sent_failed = sent_failed + :f,
                status = CASE WHEN (sent_success + sent_failed + :s + :f) >= total_numbers THEN 'Completed' ELSE 'Processing' END
            WHERE id = :id
        """, {"s": success_batch, "f": failed_batch, "id": campaign_id})

        # 5. Broadcast progress via SSE
        progress_event = json.dumps({
            "campaign_id": campaign_id,
            "success": campaign['sent_success'] + success_batch,
            "failed": campaign['sent_failed'] + failed_batch,
            "total": campaign['total_numbers'],
            "last_phone": pending_messages[-1]['phone'] if pending_messages else "...",
            "last_status": "Batch Processed",
            "is_complete": (campaign['sent_success'] + campaign['sent_failed'] + processed_count) >= campaign['total_numbers']
        })
        for queue in event_queues:
            await queue.put(progress_event)

        return {
            "completed": (campaign['sent_success'] + campaign['sent_failed'] + processed_count) >= campaign['total_numbers'],
            "processed": processed_count,
            "success": success_batch,
            "failed": failed_batch
        }

    except Exception as e:
        print(f"DEBUG ERROR in process_campaign_batch for {campaign_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "completed": False}
    
    return {
        "completed": (campaign['sent_success'] + campaign['sent_failed'] + processed_count) >= campaign['total_numbers'],
        "processed": processed_count,
        "success": success_batch,
        "failed": failed_batch
    }

@app.post("/api/campaign/process-batch/{campaign_id}")
async def process_batch_endpoint(campaign_id: int):
    return await process_campaign_batch(campaign_id)

async def process_campaign(user_id: int, campaign_id: int, data: list, phone_col: str, message_template: str, msg_type: str = "text", template_name: str = "", language_code: str = "en_US", report_email: str = None, mappings: dict = None):
    print(f"DEBUG: Starting processing for Campaign {campaign_id} with {len(data)} rows. Type: {msg_type}")
    db = await get_db()
    
    # NEW: Instead of processing here, we queue all messages as 'pending'
    # so they can be processed by the background batcher or the API call.
    for row in data:
        raw_phone = str(row.get(phone_col, ""))
        phone = normalize_phone(raw_phone)
        if not phone: continue
        
        await db.execute("""
            INSERT INTO messages (user_id, campaign_id, phone, status, row_data, timestamp)
            VALUES (:u, :cid, :p, 'pending', :r, :t)
        """, {
            "u": user_id, "cid": campaign_id, "p": phone, 
            "r": json.dumps(row), "t": get_now_utc()
        })
        
    await db.execute("UPDATE campaigns SET total_numbers = :t, status = 'Processing' WHERE id = :id", {"t": len(data), "id": campaign_id})

    # Trigger initial batch processing in background
    background_tasks.add_task(process_campaign_batch, campaign_id)
    
    return {"message": "Campaign queued", "campaign_id": campaign_id}

async def campaign_scheduler():
    """Background task that checks for scheduled campaigns and starts them."""
    print("DEBUG: Campaign Scheduler started.")
    while True:
        try:
            db = await get_db()
            now_utc = get_now_utc() # Format: YYYY-MM-DD HH:MM:SS
            
            # Find campaigns that are 'Scheduled' and have reached their time
            # We use string comparison for consistency with our date storage
            scheduled_campaigns = await db.fetch_all(
                "SELECT id FROM campaigns WHERE status = 'Scheduled' AND scheduled_at <= :now",
                {"now": now_utc}
            )
            
            for c in scheduled_campaigns:
                cid = c['id']
                print(f"SCHEDULER: Starting campaign {cid}...")
                await db.execute("UPDATE campaigns SET status = 'Processing' WHERE id = :id", {"id": cid})
                # Start processing in background
                asyncio.create_task(process_campaign_batch(cid))
                
        except Exception as e:
            print(f"SCHEDULER ERROR: {e}")
            
        await asyncio.sleep(30) # Check every 30 seconds
    
async def process_campaign_legacy(user_id: int, campaign_id: int, data: list, phone_col: str, message_template: str, msg_type: str = "text", template_name: str = "", language_code: str = "en_US", report_email: str = None, mappings: dict = None):
    print(f"DEBUG: Starting processing for Campaign {campaign_id} with {len(data)} rows. Type: {msg_type}")
    db = await get_db()
    success_count = 0
    failed_count = 0
    
    # Send initial event
    initial_event = json.dumps({
        "campaign_id": campaign_id,
        "success": 0,
        "failed": 0,
        "total": len(data),
        "last_phone": "Starting...",
        "last_status": "Starting"
    })
    for queue in event_queues:
        await queue.put(initial_event)
    
    # --- Template Intelligence: Pre-fetch template to identify Header vs Body variables ---
    template_def = None
    if msg_type == "template" and template_name:
        # Search by name (case-insensitive for safety)
        template_def = await db.fetch_one("SELECT components FROM templates WHERE LOWER(name) = LOWER(:name) AND user_id = :u LIMIT 1", {"name": template_name, "u": user_id})

    # 1. Fetch Campaign Metadata for media
    campaign_media_url = None
    try:
        camp_row = await db.fetch_one("SELECT media_url FROM campaigns WHERE id = :id", {"id": campaign_id})
        if camp_row: campaign_media_url = camp_row['media_url']
    except: pass

    for i, row in enumerate(data):
        raw_phone = str(row.get(phone_col, ""))
        phone = normalize_phone(raw_phone)
        if not phone:
            continue
            
        media_url = campaign_media_url
        message_to_send = ""
        forced_components = []

        if msg_type == "template":
            message_to_send = message_template or f"Template: {template_name}"
            
            header_params = []
            body_params = []
            
            comp_list = []
            if template_def and template_def['components']:
                try: comp_list = json.loads(template_def['components'])
                except: pass
            
            header_var_count = 0
            body_var_count = 0
            has_media_header = False
            
            if comp_list:
                for c in comp_list:
                    ctype = str(c.get('type', '')).upper()
                    ctext = str(c.get('text', ''))
                    if ctype == 'HEADER':
                        header_var_count = len(re.findall(r'\{\{\s*\d+\s*\}\}', ctext))
                        if c.get('format') in ['IMAGE', 'VIDEO', 'DOCUMENT']:
                            has_media_header = True
                    elif ctype == 'BODY':
                        body_var_count = len(re.findall(r'\{\{\s*\d+\s*\}\}', ctext))
            else:
                # FALLBACK: If template def is missing, assume 1 variable goes to BODY.
                # If you suspect it is in the header, we will try to detect from message_template
                if message_template and '{{1}}' in message_template:
                    body_var_count = 1
            
            if mappings:
                vars_map = mappings.get('vars', {})
                # Sort by numeric key
                sorted_keys = sorted(vars_map.keys(), key=lambda x: int(x))
                
                for idx, k in enumerate(sorted_keys):
                    val = str(row.get(vars_map[k], "")).strip()
                    if not val: val = " " # Meta fails on empty params
                    
                    if idx < header_var_count:
                        header_params.append({"type": "text", "text": val})
                    else:
                        body_params.append({"type": "text", "text": val})
                    
                    # Update preview
                    pattern = r'\{\{\s*' + re.escape(str(idx + 1)) + r'\s*\}\}'
                    message_to_send = re.sub(pattern, val, message_to_send, flags=re.IGNORECASE)
                
                if mappings.get('header'):
                    media_url = row.get(mappings['header'])

            # BUILD FINAL COMPONENTS
            if has_media_header and media_url:
                fmt = "image"
                if str(media_url).lower().endswith((".mp4", ".mov")): fmt = "video"
                elif str(media_url).lower().endswith((".pdf", ".doc", ".docx")): fmt = "document"
                forced_components.append({
                    "type": "header",
                    "parameters": [{"type": fmt, fmt: {"link": media_url}}]
                })
            elif header_params:
                forced_components.append({"type": "header", "parameters": header_params})
            
            if body_params:
                forced_components.append({"type": "body", "parameters": body_params})
            
            # FINAL SAFETY: If we expected a header variable but didn't send one, add a blank one
            if header_var_count > 0 and not header_params:
                 forced_components.append({"type": "header", "parameters": [{"type": "text", "text": " "}]})
            # FINAL SAFETY: If we expected a body variable but didn't send one, add a blank one
            if body_var_count > 0 and not body_params:
                 forced_components.append({"type": "body", "parameters": [{"type": "text", "text": " "}]})

            print(f"DEBUG: Smart Components for {phone}: {json.dumps(forced_components)}")
        else:
            message_to_send = substitute_template(message_template or "", row)
        
        # Human mimicry delay (Reduced for speed)
        delay = random.randint(2, 6) if USE_REAL_API else random.randint(1, 2)
        
        # Batching break (Reduced for speed)
        if USE_REAL_API and i > 0 and i % 5 == 0:
            batch_break = random.randint(10, 25)
            break_event = json.dumps({
                "campaign_id": campaign_id,
                "status_text": f"Optimizing queue ({batch_break}s)...",
                "is_waiting": True
            })
            for queue in event_queues:
                await queue.put(break_event)
            await asyncio.sleep(batch_break)
        
        # Typing status broadcast
        typing_event = json.dumps({
            "campaign_id": campaign_id,
            "status_text": f"Preparing {msg_type} to {phone} ({delay}s)...",
            "is_waiting": True
        })
        for queue in event_queues:
            await queue.put(typing_event)
        await asyncio.sleep(delay)
        
        # Auto-detect msg_type if it's text but we have a media_url
        final_msg_type = msg_type
        if msg_type == "text" and media_url:
            final_msg_type = "image"
            if str(media_url).lower().endswith((".mp4", ".mov")): final_msg_type = "video"
            elif str(media_url).lower().endswith((".pdf", ".doc", ".docx", ".xlsx", ".xls")): final_msg_type = "document"

        credentials = await get_active_credentials(user_id)
        success, response = await send_whatsapp_message(
            phone, message_to_send, final_msg_type, template_name, language_code, 
            media_url=media_url, credentials=credentials, forced_components=forced_components
        )
        
        if not success:
            print(f"DEBUG ERROR: Campaign Message Failed to {phone}. Response: {response}")
            failed_count += 1
        
        status = "sent" if success else "failed"
        error = ""
        wa_message_id = None
        
        if success:
            success_count += 1
            # Extract message ID from Meta response
            # Response is usually {'messaging_product': 'whatsapp', 'contacts': [...], 'messages': [{'id': '...'}]}
            if isinstance(response, dict) and 'messages' in response:
                wa_message_id = response['messages'][0].get('id')
                print(f"DEBUG: Campaign Message {i+1} to {phone} SUCCESS. Meta ID: {wa_message_id}")
            else:
                print(f"DEBUG: Campaign Message {i+1} to {phone} SUCCESS but ID not found in response: {response}")
        else:
            failed_count += 1
            try:
                err_data = json.loads(response) if isinstance(response, str) else response
                if isinstance(err_data, dict):
                    error = err_data.get('error', {}).get('message', str(response))
                else:
                    error = str(response)
            except:
                error = str(response)
            
        is_auth_error = False
        if not success:
            if "401" in str(error) or "OAuthException" in str(error) or "Authentication" in str(error):
                is_auth_error = True
                print(f"DEBUG: Critical Authentication Error (401) detected for Campaign {campaign_id}. Stopping campaign.")
            
        # Log message status with UTC (browser converts to local)
        now_utc = get_now_utc()
        await db.execute("""
            INSERT INTO messages (user_id, campaign_id, phone, message, status, error_message, whatsapp_message_id, row_data, timestamp)
            VALUES (:u, :campaign_id, :phone, :message, :status, :error_message, :wa_id, :row_data, :timestamp)
        """, {
            "u": user_id, "campaign_id": campaign_id, "phone": phone, "message": str(message_to_send), 
            "status": status, "error_message": error, "wa_id": wa_message_id, 
            "row_data": json.dumps(row), "timestamp": now_utc
        })
        
        # Update campaign progress
        await db.execute("""
            UPDATE campaigns 
            SET sent_success = :success, sent_failed = :failed, status = 'Processing'
            WHERE id = :id
        """, {"success": success_count, "failed": failed_count, "id": campaign_id})
        
        # Notify SSE clients
        update_data = {
            "campaign_id": campaign_id,
            "success": success_count,
            "failed": failed_count,
            "total": len(data),
            "last_phone": phone,
            "last_status": status,
            "message": str(message_to_send),
            "is_complete": False,
            "is_auth_error": is_auth_error
        }
        for queue in event_queues:
            await queue.put(json.dumps(update_data))
        
        if is_auth_error:
            await db.execute("UPDATE campaigns SET status = 'Auth Error' WHERE id = :id", {"id": campaign_id})
            break

    # Update final campaign status and counts (Safety sync)
    await db.execute("""
        UPDATE campaigns 
        SET sent_success = :success, sent_failed = :failed, status = 'Completed' 
        WHERE id = :id
    """, {"success": success_count, "failed": failed_count, "id": campaign_id})
    
    # Small delay to ensure SSE clients are ready for the final burst
    await asyncio.sleep(1)

    # Final 'Completed' event
    final_event = {
        "campaign_id": campaign_id,
        "success": success_count,
        "failed": failed_count,
        "total": len(data),
        "last_phone": "Done",
        "last_status": "Finished",
        "is_complete": True
    }
    for queue in event_queues:
        await queue.put(json.dumps(final_event))
    
    # Prepare report data from the database
    report_data = []
    msg_rows = await db.fetch_all("SELECT row_data, status, timestamp FROM messages WHERE campaign_id = :id", {"id": campaign_id})
    for r in msg_rows:
        r = dict(r)
        raw = r['row_data']
        if raw:
            try: d = json.loads(raw)
            except: d = {"Phone": "Data Error"}
        else:
            d = {"Phone": "Unknown"}
        d['Delivery Status'] = r['status']
        d['Sent At'] = r['timestamp']
        report_data.append(d)

    # Sync to Google Sheets and Send Email after all rows are processed
    try:
        if report_data:
            try:
                await asyncio.to_thread(sync_to_google_sheet, report_data, "messenger")
            except Exception as e:
                print(f"DEBUG: Sync failed: {str(e)}")
            
            if report_email and report_email.strip():
                if not SYSTEM_PASS or SYSTEM_PASS == 'your-app-password':
                    print("DEBUG: Email report skipped - SYSTEM_PASS not configured.")
                else:
                    SMTP_CONFIG = {
                        "host": "smtp.gmail.com",
                        "port": 587,
                        "user": SYSTEM_EMAIL,
                        "pass": SYSTEM_PASS
                    }
                    try:
                        await asyncio.to_thread(send_email_report, report_data, report_email, SMTP_CONFIG)
                    except Exception as e:
                        print(f"DEBUG: Email sending failed: {str(e)}")
    finally:
        # Final 'Completed' event must ALWAYS send to reset the UI button
        final_event = {
            "campaign_id": campaign_id,
            "success": success_count,
            "failed": failed_count,
            "total": len(data),
            "last_phone": "Done",
            "last_status": "Finished",
            "is_complete": True,
            "is_auth_error": False
        }
        for queue in event_queues:
            await queue.put(json.dumps(final_event))

@app.post("/clear-history")
async def clear_history():
    db = await get_db()
    # Delete messages first due to FK, then campaigns
    await db.execute("DELETE FROM messages")
    await db.execute("DELETE FROM campaigns")
    return {"message": "History cleared"}

@app.get("/export/{campaign_id}")
async def export_campaign(campaign_id: int):
    import pandas as pd
    import io
    from fastapi.responses import StreamingResponse

    db = await get_db()
    rows = await db.fetch_all("""
        SELECT row_data, status, timestamp, phone 
        FROM messages 
        WHERE campaign_id = :id
    """, {"id": campaign_id})

    if not rows:
        return JSONResponse({"error": "No data found for this campaign"}, status_code=404)

    # Reconstruct original columns + new status/time
    report_data = []
    for r in rows:
        raw = r['row_data']
        if raw:
            data = json.loads(raw)
        else:
            data = {"Phone": r['phone']}
            
        data['Delivery Status'] = r['status']
        data['Sent At'] = r['timestamp']
        report_data.append(data)

    df = pd.DataFrame(report_data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Campaign Report')
    output.seek(0)

    headers = {
        'Content-Disposition': f'attachment; filename="campaign_{campaign_id}_report.xlsx"'
    }
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

@app.post("/auth/facebook/unlink")
async def facebook_unlink(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    # Deactivate ONLY this user's credentials
    await db.execute("UPDATE user_credentials SET is_active = 0 WHERE user_id = :u", {"u": u_id})
    return {"message": "WhatsApp unlinked successfully"}

@app.post("/auth/facebook/callback")
async def facebook_auth_callback(request: Request, data: dict):
    code = data.get('code')
    access_token = data.get('access_token')
    
    # 0. Exchange code for access_token if needed (Security Upgrade)
    if code and not access_token:
        try:
            import httpx  # Local import to ensure availability
            # In Meta v2 Signup (JS SDK 'code' flow), redirect_uri must be empty or match the original
            exchange_url = "https://graph.facebook.com/v21.0/oauth/access_token"
            data_payload = {
                "client_id": FB_APP_ID, 
                "client_secret": FB_APP_SECRET, 
                "code": code,
                "redirect_uri": "" # Empty for JS SDK 'code' flow
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(exchange_url, data=data_payload)
            res_json = res.json()
            if "access_token" in res_json:
                access_token = res_json["access_token"]
            else:
                err_msg = res_json.get("error", {}).get("message", str(res_json))
                print(f"ERROR FB: Token exchange failed: {err_msg}")
                return JSONResponse({"error": f"Meta Exchange Error: {err_msg}"}, status_code=400)

        except Exception as e:
            print(f"ERROR FB: Token exchange exception: {str(e)}")
            return JSONResponse({"error": f"Token Exchange Crash: {str(e)}"}, status_code=500)

    if not access_token:
        return JSONResponse({"error": "No access token or valid code provided"}, status_code=400)
    
    # Mandatory Scan: Always find the best WABA and Phone ID regardless of frontend input
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. Scan for WABAs
        waba_url = "https://graph.facebook.com/v21.0/me/whatsapp_business_accounts"
        waba_res = requests.get(waba_url, headers=headers)
        waba_json = waba_res.json()
        waba_data = waba_json.get('data', [])
        
        selected_waba = None
        if waba_data:
            # Prefer non-test WABA
            for w in waba_data:
                if "test" not in str(w.get('name', '')).lower():
                    selected_waba = w['id']
                    break
            if not selected_waba: selected_waba = waba_data[0]['id']
            
        if not selected_waba:
            return JSONResponse({"error": "No WhatsApp Business Account found."}, status_code=404)
        
        # 2. Scan for Phone Numbers in that WABA
        phone_url = f"https://graph.facebook.com/v21.0/{selected_waba}/phone_numbers"
        phone_res = requests.get(phone_url, headers=headers)
        phone_json = phone_res.json()
        phone_data = phone_json.get('data', [])
        
        if not phone_data:
            return JSONResponse({"error": "No phone numbers found in this WABA."}, status_code=404)
            
        # Pick the best phone number
        final_phone_id = phone_data[0]['id']
        final_phone_num = phone_data[0].get('display_phone_number', 'Linked Account')
        
        for p in phone_data:
            disp = str(p.get('display_phone_number', '')).lower()
            vname = str(p.get('verified_name', '')).lower()
            # Skip Meta test number (+1 555-187-4003)
            is_test = "test" in disp or "test" in vname or "15551874003" in disp.replace(" ", "").replace("-", "").replace("+", "")
            if not is_test:
                final_phone_id = p['id']
                final_phone_num = p.get('display_phone_number', 'Linked Account')
                break
        
        waba_id = selected_waba
        phone_id = final_phone_id
        phone_number = final_phone_num
        print(f"DEBUG FB: Auto-Selected {phone_number} (ID: {phone_id}) for WABA {waba_id}")

    except Exception as e:
        print(f"DEBUG FB: Overhaul detection failed: {str(e)}")
        return JSONResponse({"error": f"Account sync failed: {str(e)}"}, status_code=500)


    db = await get_db()
    # Find user
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)

    # Deactivate existing credentials for THIS user
    await db.execute("UPDATE user_credentials SET is_active = 0 WHERE user_id = :u", {"u": u_id})
    
    # Save new credentials for THIS user
    await db.execute("""
        INSERT INTO user_credentials (user_id, whatsapp_token, phone_number_id, waba_id, phone_number, is_active)
        VALUES (:u, :token, :phone_id, :waba_id, :phone, 1)
    """, {"u": u_id, "token": access_token, "phone_id": phone_id, "waba_id": waba_id, "phone": phone_number})
    
    # SUBSCRIBE THE WABA TO OUR APP WEBHOOKS (CRITICAL FOR EMBEDDED SIGNUP)
    await subscribe_waba_to_app(waba_id, access_token)
    
    return {"message": "WhatsApp Account linked successfully!", "phone": phone_number}

@app.post("/api/auth/manual")
async def manual_auth(request: Request):
    """Allows manual entry of WABA ID, Phone ID, and Token (useful for System User tokens)."""
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)

    body = await request.json()
    token = body.get("token", "").strip() if body.get("token") else ""
    waba_id = body.get("waba_id", "").strip() if body.get("waba_id") else ""
    phone_id = body.get("phone_id", "").strip() if body.get("phone_id") else ""

    if not all([token, waba_id, phone_id]):
        return JSONResponse(status_code=400, content={"error": "All fields are required."})

    # Try to verify and get the phone number for display
    phone_number = "Manual Account"
    try:
        url = f"https://graph.facebook.com/v21.0/{phone_id}"
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            phone_number = data.get("display_phone_number", "Manual Account")
    except:
        pass

    db = await get_db()
    # Deactivate existing
    await db.execute("UPDATE user_credentials SET is_active = 0 WHERE user_id = :u", {"u": u_id})
    
    # Save new
    await db.execute("""
        INSERT INTO user_credentials (user_id, whatsapp_token, phone_number_id, waba_id, phone_number, is_active)
        VALUES (:u, :token, :phone_id, :waba_id, :phone, 1)
    """, {"u": u_id, "token": token, "phone_id": phone_id, "waba_id": waba_id, "phone": phone_number})
    
    # SUBSCRIBE THE WABA TO OUR APP WEBHOOKS
    await subscribe_waba_to_app(waba_id, token)

    return {"message": "Credentials updated successfully!", "phone": phone_number}

@app.post("/upload")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    single_mobile: str = Form(None),
    message: str = Form(None),
    msg_type: str = Form("text"),
    template_name: str = Form(None),
    language_code: str = Form("en_US"),
    report_email: str = Form(None),
    mappings: str = Form(None),
    scheduled_at: str = Form(None),
    media_url: str = Form(None),
    media_file: UploadFile = File(None)
):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    db = await get_db()
    mappings_dict = None
    if mappings:
        try:
            mappings_dict = json.loads(mappings)
        except: pass

    if single_mobile:
        single_mobile = single_mobile.strip()
        data = [{"phone": single_mobile}]
        phone_col = "phone"
        filename = "Manual Entry"
        
        if mappings_dict:
            new_mappings = {"vars": {}, "header": None}
            if "vars" in mappings_dict:
                for k, v in mappings_dict["vars"].items():
                    data[0][f"var_{k}"] = v
                    new_mappings["vars"][k] = f"var_{k}"
            if "header" in mappings_dict and mappings_dict["header"]:
                data[0]["header_url"] = mappings_dict["header"]
                new_mappings["header"] = "header_url"
            mappings_dict = new_mappings
    else:
        if not file:
            return JSONResponse(status_code=400, content={"error": "File or valid mobile number required."})
        
        content = await file.read()
        try:
            data, phone_col = extract_phone_numbers(content, file.filename)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": str(e)})
        filename = file.filename
        
    if not data or len(data) == 0:
        return JSONResponse(status_code=400, content={"error": "No valid contacts found in the uploaded file. Please ensure your file has at least one phone number."})
    now_utc = get_now_utc()
    
    # Handle media file upload if provided
    final_media_url = media_url
    if media_file and media_file.filename:
        try:
            ext = os.path.splitext(media_file.filename)[1]
            # Use a temp name first, we'll update with campaign_id if needed or just use timestamp
            unique_name = f"media_{random.randint(1000, 9999)}_{int(asyncio.get_event_loop().time())}{ext}"
            save_path = os.path.join(UPLOAD_DIR, unique_name)
            with open(save_path, "wb") as buffer:
                m_content = await media_file.read()
                buffer.write(m_content)
            # Use absolute URL if possible for Meta compatibility, or relative and handle in worker
            final_media_url = f"/static/uploads/{unique_name}"
        except Exception as e:
            print(f"DEBUG: Media upload failed: {e}")

    # 1. Create Campaign with Metadata
    status = 'Scheduled' if scheduled_at else 'Pending'
    # Format scheduled_at to match our DB string format (YYYY-MM-DD HH:MM:SS)
    final_schedule = None
    if scheduled_at:
        # datetime-local format is YYYY-MM-DDTHH:MM
        final_schedule = scheduled_at.replace('T', ' ') + ":00"

    campaign_id = await db.execute("""
        INSERT INTO campaigns (user_id, name, total_numbers, status, timestamp, 
                              message_template, msg_type, template_name, language_code, mappings, phone_col, scheduled_at, media_url) 
        VALUES (:u, :name, :total, :status, :ts, :msg, :mtype, :tname, :lang, :maps, :pcol, :sch, :murl)
    """, {
        "u": u_id, "name": filename, "total": len(data), "status": status, "ts": now_utc,
        "msg": message, "mtype": msg_type, "tname": template_name, "lang": language_code, 
        "maps": json.dumps(mappings_dict), "pcol": phone_col, "sch": final_schedule, "murl": final_media_url
    })

    # 2. Bulk Insert pending messages
    for row in data:
        raw_phone = str(row.get(phone_col, ""))
        phone = normalize_phone(raw_phone)
        if phone:
            await db.execute("""
                INSERT INTO messages (user_id, campaign_id, phone, status, row_data) 
                VALUES (:u, :c, :p, :s, :rd)
            """, {"u": u_id, "c": campaign_id, "p": phone, "s": 'pending', "rd": json.dumps(row)})
    
    return {"message": "Campaign queued", "campaign_id": campaign_id, "total": len(data)}

@app.post("/api/campaigns/{campaign_id}/process")
async def process_batch_endpoint(request: Request, campaign_id: int):
    session_token = request.cookies.get("session_token")
    if not verify_session_token(session_token):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    # Process batch of 5
    try:
        result = await process_campaign_batch(campaign_id, batch_size=5)
        return result
    except Exception as e:
        print(f"DEBUG CRITICAL: process_batch_endpoint error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/events")
async def events_handler(request: Request):
    queue = asyncio.Queue()
    event_queues.append(queue)
    
    async def event_generator():
        try:
            while True:
                # Check if client is still connected
                if await request.is_disconnected():
                    break
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_queues.remove(queue)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/templates")
@app.get("/api/templates")
async def get_templates_route(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    rows = await db.fetch_all("SELECT * FROM templates WHERE user_id = :u", {"u": u_id})
    return safe_json_response([dict(r) for r in rows])

@app.post("/templates/sync")
@app.post("/api/templates/sync")
async def sync_templates(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    credentials = await get_active_credentials(u_id)
    if not credentials:
        return JSONResponse(status_code=400, content={"error": "Please link your WhatsApp account first."})
    
    # fix lint: ensure credentials is a dict
    waba_id = credentials.get('waba_id') if isinstance(credentials, dict) else None
    print(f"DEBUG: Syncing templates for WABA: {waba_id}")
    # fetch_meta_templates returns [] on error or if no templates exist.
    # We should distinguish between "Not Linked" and "Empty".
    templates_data = await fetch_meta_templates(credentials)
    print(f"DEBUG: Meta API returned {len(templates_data)} templates.")
    
    db = await get_db()
    scheme = str(db.url.scheme).lower()
    print(f"DEBUG: Database scheme is: '{scheme}'")
    is_mysql = "mysql" in scheme or "mariadb" in scheme
    sync_count = 0
    for t in templates_data:
        name = t.get('name')
        category = t.get('category')
        language = t.get('language')
        status = t.get('status')
        content = t.get('content')
        components = t.get('components')
        print(f"DEBUG SYNC: Template '{name}' Category from Meta: {category}")
        
        utc_now = get_now_utc()
        if is_mysql:
            query = """
                INSERT INTO templates (user_id, name, category, language, status, content, components, last_synced)
                VALUES (:u, :name, :category, :language, :status, :content, :components, :last_synced)
                ON DUPLICATE KEY UPDATE
                    category = VALUES(category),
                    language = VALUES(language),
                    status = VALUES(status),
                    content = VALUES(content),
                    components = VALUES(components),
                    last_synced = VALUES(last_synced)
            """
        else:
            query = """
                INSERT INTO templates (user_id, name, category, language, status, content, components, last_synced)
                VALUES (:u, :name, :category, :language, :status, :content, :components, :last_synced)
                ON CONFLICT(user_id, name) DO UPDATE SET
                    category = excluded.category,
                    language = excluded.language,
                    status = excluded.status,
                    content = excluded.content,
                    components = excluded.components,
                    last_synced = :last_synced
            """
            
        await db.execute(query, {
            "u": u_id,
            "name": name, "category": category, "language": language, 
            "status": status, "content": content, "components": components,
            "last_synced": utc_now
        })
        print(f"DEBUG: Successfully synced template: {name}")
        sync_count += 1
    
    # NEW: Cleanup local templates that are no longer on Meta
    meta_names = {t.get('name') for t in templates_data}
    local_rows = await db.fetch_all("SELECT name FROM templates")
    for row in local_rows:
        if row['name'] not in meta_names:
            await db.execute("DELETE FROM templates WHERE name = :name", {"name": row['name']})
    
    return safe_json_response({"message": f"Synced {sync_count} templates from Meta"})

@app.post("/api/templates/delete")
async def delete_template_api(request: Request, name: str = Form(...)):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    credentials = await get_active_credentials(u_id)
    db = await get_db()
    
    # 1. Attempt to delete from Meta
    try:
        success, msg = await delete_whatsapp_template(name, credentials)
        print(f"DEBUG: Meta delete response for {name}: {success}, {msg}")
    except Exception as e:
        print(f"ERROR: Exception during Meta delete: {e}")
    
    # 2. Always delete locally to keep UI clean
    await db.execute("DELETE FROM templates WHERE name = :name AND user_id = :u", {"name": name, "u": u_id})
    
    return {"message": "Template deleted successfully"}

@app.post("/api/templates/create-complex")
async def create_complex_template(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    subtype: str = Form("DEFAULT"),
    language: str = Form("en_US"),
    content: str = Form(...),
    footer: str = Form(None),
    header_type: str = Form("NONE"),
    header_text: str = Form(None),
    buttons: str = Form("[]"), # JSON string
    variable_map: str = Form(None) # JSON string of {"1": "name", "2": "city"}
):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    credentials = await get_active_credentials(u_id)
    if not credentials:
        print(f"ERROR: Template creation failed for user {username} (ID: {u_id}) - No active credentials.")
        return JSONResponse(status_code=400, content={"error": "Active WhatsApp credentials not found. Please go to the 'Link Account' tab and re-link your WhatsApp account to activate it."})
    
    # Normalize newlines in body content
    # 1. Convert Windows \r\n to standard \n
    content = content.replace('\r\n', '\n')
    # 2. Collapse 3 or more consecutive newlines into exactly 2 (preserves paragraph breaks without massive gaps)
    import re
    content = re.sub(r'\n{3,}', '\n\n', content).strip()

    # Construct Meta Components
    components = []
    
    # 1. Header
    h_text = (header_text or "").strip()
    # Refined cleanup: Only remove characters that are DEFINITELY forbidden in headers
    # We avoid .isprintable() as it can sometimes mangle emojis.
    clean_header = h_text.replace('\n', ' ').replace('\r', '').replace('*', '').replace('_', '').replace('~', '').replace('`', '')
    if header_type and header_type != "NONE":
        if header_type == "TEXT":
            if h_text:
                # Meta is extremely strict about the header for some accounts. 
                # Emojis/formatting causing "Header format is incorrect".
                # We strip all non-ASCII to guarantee creation success, BUT 
                # we must preserve {{n}} if the user intended a variable.
                # Find all {{n}} first, then clean the rest.
                header_vars = re.findall(r'\{\{\s*(\d+)\s*\}\}', h_text)
                
                # Simple cleanup while preserving braces for variables
                safe_header = "".join(c for c in h_text if ord(c) < 128 or c in '{}').strip()
                if not safe_header: safe_header = "Welcome" 
                
                header_comp = {"type": "HEADER", "format": "TEXT", "text": safe_header}
                if header_vars:
                    # Meta requires example for header variables too
                    max_h_idx = max(int(m) for m in header_vars)
                    header_comp["example"] = {"header_text": ["sample" for _ in range(max_h_idx)]}
                
                components.append(header_comp)
        else:
            # Media headers (IMAGE, VIDEO, DOCUMENT)
            handle = None
            upload_error = "Unknown Error"
            
            print(f"DEBUG: Media header requested. Sample text: {h_text}")
            
            if h_text and "/static/uploads/" in h_text:
                try:
                    filename = h_text.split("/")[-1]
                    # Use the globally defined UPLOAD_DIR
                    local_path = os.path.join(UPLOAD_DIR, filename)
                    print(f"DEBUG: Looking for local file at: {local_path}")
                    
                    if os.path.exists(local_path):
                        with open(local_path, "rb") as f:
                            file_bytes = f.read()
                        
                        from whatsapp_service import get_meta_header_handle
                        # Detect MIME type
                        ext = filename.split(".")[-1].lower()
                        mime_map = {
                            "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                            "mp4": "video/mp4", "pdf": "application/pdf"
                        }
                        mime = mime_map.get(ext, "image/jpeg")
                        
                        handle, upload_error = await get_meta_header_handle(file_bytes, mime, credentials)
                        if handle:
                            print(f"DEBUG: Successfully obtained header_handle: {handle}")
                        else:
                            print(f"DEBUG: Meta handle creation failed: {upload_error}")
                    else:
                        upload_error = f"File not found on server: {local_path}"
                        print(f"DEBUG: {upload_error}")
                except Exception as e:
                    upload_error = str(e)
                    print(f"DEBUG: Exception during handle creation: {upload_error}")
            else:
                upload_error = "No valid sample media URL provided. Please upload an image/video/document."
                print(f"DEBUG: {upload_error}")

            if not handle:
                return JSONResponse(status_code=400, content={"error": f"Media Header Error: {upload_error}. Media templates REQUIRE a valid sample file to be uploaded and registered with Meta."})

            components.append({
                "type": "HEADER", 
                "format": header_type, 
                "example": {"header_handle": [handle]}
            })


    # 2. Body
    # Meta requires exactly n examples for variables {{1}} through {{n}}.
    found_var_indices = [int(m) for m in re.findall(r'\{\{\s*(\d+)\s*\}\}', content)]
    if found_var_indices:
        max_idx = max(found_var_indices)
        # Use the names from variable_map for better approval speed
        v_map = json.loads(variable_map or "{}")
        example_values = [v_map.get(str(i), "sample") for i in range(1, max_idx + 1)]
        
        components.append({
            "type": "BODY", 
            "text": content, 
            "example": {
                "body_text": [example_values]
            }
        })
    else:
        components.append({"type": "BODY", "text": content})
    
    # 3. Footer
    if footer:
        components.append({"type": "FOOTER", "text": footer})
        
    # 4. Buttons
    btn_list = json.loads(buttons)
    if btn_list:
        meta_btns = []
        for b in btn_list:
            if b['type'] == 'QUICK_REPLY':
                meta_btns.append({"type": "QUICK_REPLY", "text": b['text']})
            elif b['type'] == 'PHONE_NUMBER':
                meta_btns.append({"type": "PHONE_NUMBER", "text": b['text'], "phone_number": b.get('phone', '')})
            elif b['type'] == 'URL':
                url_val = b.get('url', '')
                if '{{1}}' in url_val:
                    meta_btns.append({
                        "type": "URL", 
                        "text": b['text'], 
                        "url": url_val,
                        "example": ["https://example.com/sample"] # Meta requires example for dynamic URLs
                    })
                else:
                    meta_btns.append({"type": "URL", "text": b['text'], "url": url_val})
        
        if meta_btns:
            components.append({"type": "BUTTONS", "buttons": meta_btns})

    # Debug logging
    print(f"DEBUG: Constructing Meta Template with components: {json.dumps(components, indent=2)}")

    # Call Meta API
    success, error_msg = create_whatsapp_template(
        name=name, 
        category=category, 
        language=language, 
        components=components, 
        credentials=credentials,
        subtype=subtype
    )
    
    if not success:
        return JSONResponse(status_code=400, content={"error": error_msg})
    
    # Enrich components with the original URL for local preview purposes
    if header_type in ['IMAGE', 'VIDEO', 'DOCUMENT'] and h_text:
        for comp in components:
            if comp.get('type') == 'HEADER':
                if 'example' not in comp: comp['example'] = {}
                comp['example']['_original_url'] = h_text

    # Save to Local DB
    db = await get_db()
    is_mysql = "mysql" in str(db.url.scheme).lower() or "mariadb" in str(db.url.scheme).lower()
    
    utc_now = get_now_utc()
    if is_mysql:
        query = """
            INSERT INTO templates (user_id, name, category, language, status, content, components, variable_map, last_synced, media_url)
            VALUES (:u_id, :name, :category, :language, :status, :content, :components, :var_map, :last_synced, :murl)
            ON DUPLICATE KEY UPDATE
                category = VALUES(category),
                language = VALUES(language),
                status = 'PENDING',
                content = VALUES(content),
                components = VALUES(components),
                variable_map = VALUES(variable_map),
                last_synced = VALUES(last_synced),
                media_url = VALUES(media_url)
        """
    else:
        query = """
            INSERT INTO templates (user_id, name, category, language, status, content, components, variable_map, last_synced, media_url)
            VALUES (:u_id, :name, :category, :language, :status, :content, :components, :var_map, :last_synced, :murl)
            ON CONFLICT(user_id, name) DO UPDATE SET
                category = excluded.category,
                language = excluded.language,
                status = 'PENDING',
                content = excluded.content,
                components = excluded.components,
                variable_map = excluded.variable_map,
                last_synced = excluded.last_synced,
                media_url = excluded.media_url
        """

    await db.execute(query, {
        "u_id": u_id, "name": name, "category": category, "language": language, 
        "status": 'PENDING', "content": content, "components": json.dumps(components), 
        "var_map": variable_map, "last_synced": utc_now, "murl": h_text if header_type in ['IMAGE', 'VIDEO', 'DOCUMENT'] else None
    })
    
    return {"message": "Template created and submitted to Meta!"}

@app.post("/api/get-columns")
async def get_columns(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename.lower()
        if filename.endswith(".csv"):
            import csv
            from io import StringIO
            try:
                decoded = content.decode('utf-8')
            except UnicodeDecodeError:
                decoded = content.decode('latin-1')
            f = StringIO(decoded)
            reader = csv.reader(f)
            headers = next(reader)
            return {"columns": headers}
        elif filename.endswith((".xlsx", ".xls")):
            import pandas as pd
            from io import BytesIO
            df = pd.read_excel(BytesIO(content), nrows=1)
            return {"columns": df.columns.tolist()}
        return {"columns": []}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Could not read file headers: {str(e)}"})

@app.get("/api/templates")
async def get_templates_api():
    db = await get_db()
    rows = await db.fetch_all("SELECT * FROM templates ORDER BY last_synced DESC")
    return safe_json_response([dict(r) for r in rows])

@app.get("/api/history")
async def get_history(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    # Calculate all stats dynamically from the messages table to reflect real-time Webhook updates
    rows = await db.fetch_all("""
        SELECT c.id, c.name, c.timestamp, c.total_numbers, c.status as campaign_status,
               (SELECT COUNT(*) FROM messages WHERE campaign_id = c.id AND (status = 'sent' OR status = 'delivered' OR status = 'read')) as sent_success,
               (SELECT COUNT(*) FROM messages WHERE campaign_id = c.id AND status = 'delivered') as delivered,
               (SELECT COUNT(*) FROM messages WHERE campaign_id = c.id AND status = 'read') as `read`,
               (SELECT COUNT(*) FROM messages WHERE campaign_id = c.id AND status = 'failed') as failed
        FROM campaigns c 
        WHERE c.user_id = :u
        ORDER BY timestamp DESC
    """, {"u": u_id})
    return safe_json_response([dict(r) for r in rows])

@app.get("/api/campaign/{campaign_id}/details")
async def get_campaign_details(request: Request, campaign_id: int):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    # Verify ownership
    camp = await db.fetch_one("SELECT id FROM campaigns WHERE id = :id AND user_id = :u", {"id": campaign_id, "u": u_id})
    if not camp: return JSONResponse(status_code=403, content={"error": "Forbidden"})

    # Summary stats
    stats = await db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
            SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered,
            SUM(CASE WHEN status = 'read' THEN 1 ELSE 0 END) as `read`,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM messages WHERE campaign_id = :id AND user_id = :u
    """, {"id": campaign_id, "u": u_id})
    
    # Message list
    messages = await db.fetch_all("""
        SELECT phone, status, error_message, timestamp 
        FROM messages 
        WHERE campaign_id = :id AND user_id = :u
        ORDER BY timestamp ASC
    """, {"id": campaign_id, "u": u_id})
    return safe_json_response({
        "stats": dict(stats),
        "messages": [dict(m) for m in messages]
    })

# --- Meta Webhook Handlers ---

@app.get("/webhook")
async def webhook_verify(request: Request):
    # Meta verification: hub.mode, hub.verify_token, hub.challenge
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        print("DEBUG WEBHOOK: Verified successfully!")
        return HTMLResponse(content=challenge, status_code=200)
    else:
        print("DEBUG WEBHOOK: Verification failed.")
        return JSONResponse(status_code=403, content={"error": "Verification failed"})

@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    db = await get_db()
    
    # LOG THE RAW PAYLOAD FOR DEBUGGING
    try:
        await db.execute("INSERT INTO webhook_logs (payload) VALUES (:p)", {"p": json.dumps(data)})
        # Keep only last 50 logs to save space
        await db.execute("DELETE FROM webhook_logs WHERE id NOT IN (SELECT id FROM (SELECT id FROM webhook_logs ORDER BY id DESC LIMIT 50) as t)")
    except Exception as e:
        print(f"DEBUG WEBHOOK LOG ERROR: {e}")
    print(f"DEBUG WEBHOOK: Received update: {json.dumps(data)}")

    # Check if it's a WhatsApp status update
    try:
        entries = data.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Dynamic User Routing via Meta Metadata
                metadata = value.get("metadata", {})
                pn_id = metadata.get("phone_number_id")
                print(f"DEBUG WEBHOOK: Data: {json.dumps(data)}")
                print(f"DEBUG WEBHOOK: Metadata Phone ID: {pn_id}")
                
                db = await get_db()
                cred = await db.fetch_one("SELECT user_id FROM user_credentials WHERE phone_number_id = :p LIMIT 1", {"p": str(pn_id)})
                u_id = cred['user_id'] if cred else None
                print(f"DEBUG WEBHOOK: Initial u_id lookup: {u_id}")
                
                statuses = value.get("statuses", [])
                
                for status_update in statuses:
                    wa_message_id = status_update.get("id")
                    new_status = status_update.get("status") # sent, delivered, read, failed
                    print(f"DEBUG WEBHOOK: Received {new_status} update for ID: {wa_message_id}")
                    
                    db = await get_db()
                    # 1. Update Campaigns/Bulk Messages Table
                    msg = await db.fetch_one("SELECT id, status FROM messages WHERE whatsapp_message_id = :id", {"id": wa_message_id})
                    
                    # 2. Update Individual Chat Messages Table
                    chat_msg = await db.fetch_one("SELECT id, status FROM chat_messages WHERE wa_message_id = :id", {"id": wa_message_id})
                    
                    if not msg and not chat_msg:
                        # RACE CONDITION FIX: Wait and retry once if not found
                        print(f"DEBUG WEBHOOK: ID {wa_message_id} not found initially. Retrying in 2 seconds...")
                        await asyncio.sleep(2)
                        msg = await db.fetch_one("SELECT id, status FROM messages WHERE whatsapp_message_id = :id", {"id": wa_message_id})
                        chat_msg = await db.fetch_one("SELECT id, status FROM chat_messages WHERE wa_message_id = :id", {"id": wa_message_id})

                    if not msg and not chat_msg:
                        print(f"DEBUG WEBHOOK: Message ID {wa_message_id} NOT FOUND in database (checked 'messages' and 'chat_messages')")
                    
                    if msg or chat_msg:
                        table_name = 'messages' if msg else 'chat_messages'
                        old_status = msg['status'] if msg else chat_msg['status']
                        print(f"DEBUG WEBHOOK: Updating {table_name} for {wa_message_id}: {old_status} -> {new_status}")
                        
                        # Update message status and error message if failed
                        error_msg = None
                        if new_status == 'failed':
                            errors = status_update.get("errors", [])
                            if errors:
                                error_msg = errors[0].get("message", "Unknown Meta Error")
                        
                        if error_msg:
                            if msg:
                                await db.execute("UPDATE messages SET status = :status, error_message = :err WHERE whatsapp_message_id = :id", {"status": new_status, "err": error_msg, "id": wa_message_id})
                            if chat_msg:
                                await db.execute("UPDATE chat_messages SET status = :status, error_message = :err WHERE wa_message_id = :id", {"status": new_status, "err": error_msg, "id": wa_message_id})
                        else:
                            if msg:
                                await db.execute("UPDATE messages SET status = :status WHERE whatsapp_message_id = :id", {"status": new_status, "id": wa_message_id})
                            if chat_msg:
                                await db.execute("UPDATE chat_messages SET status = :status WHERE wa_message_id = :id", {"status": new_status, "id": wa_message_id})
                        
                        # BROADCAST to Live UI (SSE)
                        update_event = json.dumps({
                            "type": "status_update",
                            "wa_id": wa_message_id,
                            "new_status": new_status
                        })
                        for queue in event_queues:
                            await queue.put(update_event)
                    else:
                        print(f"DEBUG WEBHOOK: Message ID {wa_message_id} not found in DB")
                # Check if it's an incoming message
                incoming_messages = value.get("messages", [])
                for msg_data in incoming_messages:
                    wa_message_id = msg_data.get("id")
                    from_phone = msg_data.get("from")
                    msg_type = msg_data.get("type")
                    
                    # Fallback User ID lookup if phone_number_id failed
                    # We check who was the last user to message this phone number
                    if u_id is None:
                        print(f"DEBUG WEBHOOK: u_id is None for inbound from {from_phone}. Attempting fallback lookup...")
                        last_msg = await db.fetch_one("SELECT user_id FROM messages WHERE phone LIKE :p ORDER BY timestamp DESC LIMIT 1", {"p": f"%{from_phone[-10:]}"})
                        if not last_msg:
                            last_msg = await db.fetch_one("SELECT user_id FROM chat_messages WHERE phone LIKE :p ORDER BY timestamp DESC LIMIT 1", {"p": f"%{from_phone[-10:]}"})
                        
                        if last_msg:
                            u_id = last_msg['user_id']
                            print(f"DEBUG WEBHOOK: Fallback u_id found: {u_id}")
                        else:
                            # Final fallback: just use the first active admin user if any
                            first_user = await db.fetch_one("SELECT id FROM users WHERE is_approved = 1 LIMIT 1")
                            u_id = first_user['id'] if first_user else None
                            print(f"DEBUG WEBHOOK: Final fallback u_id: {u_id}")

                    body = ""
                    if msg_type == "text":
                        body = msg_data.get("text", {}).get("body")
                    elif msg_type in ["image", "video", "document", "audio"]:
                        m_data = msg_data.get(msg_type, {})
                        m_id = m_data.get("id")
                        m_caption = m_data.get("caption", "")
                        # Store as JSON for the UI to recognize
                        body = json.dumps({
                            "is_media": True,
                            "media_type": msg_type,
                            "media_id": m_id,
                            "caption": m_caption,
                            "filename": m_data.get("filename")
                        })
                    else:
                        body = f"[Received {msg_type}]"

                    db = await get_db()
                    # Avoid duplicates
                    existing = await db.fetch_one("SELECT id FROM chat_messages WHERE wa_message_id = :id", {"id": wa_message_id})
                    if not existing:
                        clean_from = normalize_phone(from_phone)
                        await db.execute("""
                            INSERT INTO chat_messages (user_id, phone, message, direction, wa_message_id, is_read, timestamp)
                            VALUES (:u, :phone, :message, 'inbound', :id, 0, :ts)
                        """, {"u": u_id, "phone": clean_from, "message": body, "id": wa_message_id, "ts": get_now_utc()})
                        print(f"DEBUG WEBHOOK: Saved inbound {msg_type} from {clean_from} for user {u_id}")
                
    except Exception as e:
        print(f"DEBUG WEBHOOK: Error processing: {str(e)}")

    return {"status": "ok"}

@app.get("/api/chat/media/{media_id}")
async def proxy_whatsapp_media(media_id: str, request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    acc = await db.fetch_one("SELECT whatsapp_token FROM user_credentials WHERE is_active = 1 AND user_id = :u LIMIT 1", {"u": u_id})
    if not acc: return JSONResponse(status_code=400, content={"error": "Account not linked"})
    
    token = acc['whatsapp_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 1. Get Media URL from Meta
        import requests
        res = requests.get(f"https://graph.facebook.com/v21.0/{media_id}", headers=headers)
        if res.status_code != 200:
            return JSONResponse(status_code=res.status_code, content={"error": "Failed to get media URL from Meta"})
        
        media_url = res.json().get("url")
        if not media_url:
            return JSONResponse(status_code=404, content={"error": "Media URL not found in Meta response"})
            
        # 2. Stream the media bytes
        from fastapi.responses import StreamingResponse
        media_res = requests.get(media_url, headers=headers, stream=True)
        return StreamingResponse(
            media_res.iter_content(chunk_size=1024*10),
            media_type=media_res.headers.get("Content-Type", "application/octet-stream")
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/get-columns")
async def get_columns(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename.lower()
        if filename.endswith(".csv"):
            import csv
            from io import StringIO
            try:
                decoded = content.decode('utf-8')
            except UnicodeDecodeError:
                decoded = content.decode('latin-1')
            f = StringIO(decoded)
            reader = csv.reader(f)
            headers = next(reader)
            return {"columns": headers}
        elif filename.endswith((".xlsx", ".xls")):
            import pandas as pd
            from io import BytesIO
            df = pd.read_excel(BytesIO(content), nrows=1)
            return {"columns": df.columns.tolist()}
        return {"columns": []}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Could not read file headers: {str(e)}"})

@app.get("/api/templates")
async def get_templates_api():
    db = await get_db()
    rows = await db.fetch_all("SELECT * FROM templates ORDER BY last_synced DESC")
    return safe_json_response([dict(r) for r in rows])

@app.get("/api/chat/contacts")
async def get_chat_contacts(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    # Unique phones and their unread status filtered by user_id
    rows = await db.fetch_all("""
        SELECT t.phone, 
               MAX(CASE WHEN c.is_read = 0 AND c.direction = 'inbound' THEN 1 ELSE 0 END) as has_unread
        FROM (
            SELECT phone FROM messages WHERE user_id = :u AND status IN ('sent', 'delivered', 'read')
            UNION
            SELECT phone FROM chat_messages WHERE user_id = :u
        ) t
        LEFT JOIN chat_messages c ON t.phone = c.phone AND c.user_id = :u
        WHERE t.phone IS NOT NULL AND t.phone != ''
        GROUP BY t.phone
        ORDER BY MAX(c.timestamp) DESC, t.phone ASC
    """, {"u": u_id})
    return [{"phone": r['phone'], "has_unread": bool(r['has_unread'])} for r in rows]

@app.post("/api/chat/read/{phone}")
async def mark_chat_read(phone: str):
    db = await get_db()
    await db.execute("""
        UPDATE chat_messages 
        SET is_read = 1 
        WHERE phone = :p AND direction = 'inbound' AND is_read = 0
    """, {"p": phone})
    return {"status": "ok"}

@app.post("/api/templates/update")
async def update_template_api(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    body_text: str = Form(...),
    components_json: Optional[str] = Form(None)
):
    """Updates an existing WhatsApp template."""
    import json
    from whatsapp_service import update_whatsapp_template
    
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    credentials = await get_active_credentials(u_id)
    if not credentials:
        return JSONResponse({"error": "No active WhatsApp account linked"}, status_code=401)
    
    components = None
    if components_json:
        try:
            components = json.loads(components_json)
        except:
            pass

    success, message = update_whatsapp_template(
        name=name,
        category=category,
        body_text=body_text,
        components=components,
        credentials=credentials
    )

    if success:
        # Sync immediately to update local cache
        await sync_templates()
        return {"message": "Template updated successfully", "meta_response": message}
    else:
        return JSONResponse({
            "error": "Failed to update template on Meta",
            "details": message
        }, status_code=400)

@app.get("/api/chat/history/{phone}")
async def get_chat_history(request: Request, phone: str):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    # Bi-directional history filtered by user_id
    rows = await db.fetch_all("""
        SELECT 'outbound' as direction, message, timestamp, status as wa_status, NULL as wa_message_id
        FROM messages 
        WHERE phone = :p AND user_id = :u AND status != 'failed'
        UNION ALL
        SELECT direction, message, timestamp, NULL as wa_status, wa_message_id
        FROM chat_messages
        WHERE phone = :p AND user_id = :u
        ORDER BY timestamp ASC
    """, {"p": phone, "u": u_id})
    
    return safe_json_response([dict(r) for r in rows])

@app.post("/api/chat/send")
async def send_chat_reply(
    request: Request,
    phone: str = Form(...),
    message: str = Form(""),
    file: UploadFile = File(None),
    template_name: str = Form(None),
    msg_type: str = Form("text"),
    language_code: str = Form("en_US")
):
    if not phone:
        return JSONResponse(status_code=400, content={"error": "Phone number is required"})
    
    phone = normalize_phone(phone)
    
    if not message and not file and not template_name:
        return JSONResponse(status_code=400, content={"error": "Message, file, or template is required"})

    # Get Credentials for THIS user
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    # Ensure we use the logged-in user's credentials
    acc = await db.fetch_one("SELECT whatsapp_token, phone_number_id, waba_id FROM user_credentials WHERE is_active = 1 AND user_id = :u ORDER BY last_updated DESC LIMIT 1", {"u": u_id})
    if not acc:
        return JSONResponse(status_code=400, content={"error": "No WhatsApp account linked for your profile"})
    
    credentials = {
        "token": acc['whatsapp_token'],
        "phone_id": acc['phone_number_id'],
        "waba_id": acc['waba_id']
    }

    display_message = message
    media_id = None
    if msg_type == "template":
        if not template_name:
            return JSONResponse(status_code=400, content={"error": "template_name is required for template messages"})
        display_message = f"[Template: {template_name}]"
    elif file:
        file_bytes = await file.read()
        mime_type = file.content_type
        filename = file.filename
        
        db = await get_db()
        
        # Determine msg_type
        if mime_type.startswith("image/"): msg_type = "image"
        elif mime_type.startswith("video/"): msg_type = "video"
        elif mime_type.startswith("audio/"): msg_type = "audio"
        else: msg_type = "document"

        # Upload to Meta
        media_id = await upload_whatsapp_media(file_bytes, filename, mime_type, credentials)
        if not media_id:
            return JSONResponse(status_code=500, content={"error": "Failed to upload media to WhatsApp"})
        
        if not display_message:
            display_message = f"[Sent {msg_type}: {filename}]"
        else:
            display_message = f"{display_message}\n[File: {filename}]"

    # Send via Meta
    success, response = await send_whatsapp_message(
        phone=phone,
        message=message,
        msg_type=msg_type,
        media_id=media_id,
        template_name=template_name,
        language_code=language_code,
        credentials=credentials
    )
    
    print(f"DEBUG CHAT: Send to {phone} result: {success}. Response: {response}")
    
    if success:
        wa_id = None
        if isinstance(response, dict) and 'messages' in response:
            wa_id = response['messages'][0].get('id')
        
        if not wa_id:
            print(f"DEBUG CHAT: Message sent to {phone} but could not extract ID from: {response}")
            
        # Save to Chat History with user_id and initial status
        await db.execute("""
            INSERT INTO chat_messages (user_id, phone, message, direction, wa_message_id, status, is_read, timestamp)
            VALUES (:u, :phone, :message, 'outbound', :id, 'sent', 1, :ts)
        """, {"u": u_id, "phone": phone, "message": display_message, "id": wa_id, "ts": get_now_utc()})
        
        return {"status": "ok", "wa_id": wa_id}
    else:
        err_msg = str(response)
        error_code = "UNKNOWN"
        if "24 hours" in err_msg or "outside of allowed window" in err_msg or "131047" in err_msg:
            error_code = "WINDOW_CLOSED"
            err_msg = "The 24-hour window has closed. You must use a Template to message this user."
        
        return JSONResponse(status_code=400, content={"error": err_msg, "code": error_code})

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from whatsapp_service import update_whatsapp_template

class TemplateComponentReq(BaseModel):
    type: str
    format: Optional[str] = None
    text: Optional[str] = None
    example: Optional[Dict[str, Any]] = None
    buttons: Optional[List[Dict[str, Any]]] = None

class TemplateFormJSONReq(BaseModel):
    name: str
    category: str
    language: str = "en_US"
    components: List[TemplateComponentReq]

@app.put("/api/templates/update")
async def update_template_json(request: Request, req: TemplateFormJSONReq):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    credentials = await get_active_credentials(u_id)
    
    success, error_msg = update_whatsapp_template(
        name=req.name, 
        category=req.category, 
        components=[c.dict(exclude_none=True) for c in req.components], 
        credentials=credentials
    )
    
    if not success:
        return JSONResponse(status_code=400, content={"error": error_msg})
        
    # Sync with Meta to get the updated status/components
    await sync_templates()
        
    return {"message": "Template updated successfully on Meta."}

@app.post("/api/templates/create")
async def create_template_json(request: Request, req: TemplateFormJSONReq):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    credentials = await get_active_credentials(u_id)
    
    success, error_msg = create_whatsapp_template(
        name=req.name, 
        category=req.category,
        language=req.language,
        components=[c.dict(exclude_none=True) for c in req.components], 
        credentials=credentials
    )
    
    if not success:
        return JSONResponse(status_code=400, content={"error": error_msg})
    
    # Extract content from components for local preview
    content = ""
    for component in req.components:
        if component.type == "BODY":
            content = component.text or ""
            break
            
    # Save to local DB immediately so preview works
    db = await get_db()
    utc_now = get_now_utc()
    
    # Use the same logic as sync_templates but for a single template
    is_mysql = "mysql" in str(db.url).lower() or "mariadb" in str(db.url).lower()
    if is_mysql:
        query = """
            INSERT INTO templates (name, category, language, status, content, components, last_synced)
            VALUES (:name, :category, :language, 'PENDING', :content, :components, :last_synced)
            ON DUPLICATE KEY UPDATE
                category = VALUES(category),
                language = VALUES(language),
                status = 'PENDING',
                content = VALUES(content),
                components = VALUES(components),
                last_synced = VALUES(last_synced)
        """
    else:
        query = """
            INSERT INTO templates (name, category, language, status, content, components, last_synced)
            VALUES (:name, :category, :language, 'PENDING', :content, :components, :last_synced)
            ON CONFLICT(name) DO UPDATE SET
                category = excluded.category,
                language = excluded.language,
                status = 'PENDING',
                content = excluded.content,
                components = excluded.components,
                last_synced = :last_synced
        """
        
    await db.execute(query, {
        "name": req.name, "category": req.category, "language": req.language, 
        "content": content, "components": json.dumps([c.dict(exclude_none=True) for c in req.components]), 
        "last_synced": utc_now
    })
        
    return {"message": "Template created successfully on Meta and synced locally."}

@app.post("/api/templates/create-otp")
async def create_otp_template(request: Request):
    """Endpoint for creating specialized WhatsApp Authentication (OTP) templates."""
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)

    credentials = await get_active_credentials(u_id)
    if not credentials:
        return JSONResponse(status_code=400, content={"error": "Please link your WhatsApp account first."})

    body = await request.json()
    name = body.get("name", "").strip().lower().replace(" ", "_")
    language = body.get("language", "en_US")
    add_security = body.get("add_security_recommendation", False)
    expiry_minutes = body.get("code_expiration_minutes", 10)

    if not name:
        return JSONResponse(status_code=400, content={"error": "Template name is required."})

    success, resp_text = create_whatsapp_otp_template(
        name=name,
        language=language,
        add_security_recommendation=add_security,
        code_expiration_minutes=expiry_minutes,
        credentials=credentials
    )

    if not success:
        try:
            error_detail = json.loads(resp_text).get("error", {}).get("message", resp_text)
        except Exception:
            error_detail = resp_text
        return JSONResponse(status_code=400, content={"error": error_detail})

    # Build a representative body text for local preview
    body_text = "{{1}} is your verification code."
    if add_security:
        body_text += " For your security, do not share this code."

    components_preview = [
        {"type": "BODY", "text": body_text},
        {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE", "text": "Copy code"}]}
    ]
    if expiry_minutes and int(expiry_minutes) > 0:
        components_preview.append({"type": "FOOTER", "code_expiration_minutes": int(expiry_minutes)})

    # Save locally so preview works immediately
    db = await get_db()
    utc_now = get_now_utc()
    is_mysql = "mysql" in str(db.url).lower() or "mariadb" in str(db.url).lower()
    if is_mysql:
        query = """
            INSERT INTO templates (user_id, name, category, language, status, content, components, last_synced)
            VALUES (:user_id, :name, 'AUTHENTICATION', :language, 'PENDING', :content, :components, :last_synced)
            ON DUPLICATE KEY UPDATE
                category = VALUES(category),
                status = 'PENDING',
                content = VALUES(content),
                components = VALUES(components),
                last_synced = VALUES(last_synced)
        """
    else:
        query = """
            INSERT INTO templates (user_id, name, category, language, status, content, components, last_synced)
            VALUES (:user_id, :name, 'AUTHENTICATION', :language, 'PENDING', :content, :components, :last_synced)
            ON CONFLICT(user_id, name) DO UPDATE SET
                category = excluded.category,
                status = 'PENDING',
                content = excluded.content,
                components = excluded.components,
                last_synced = :last_synced
        """
    await db.execute(query, {
        "name": name, "language": language, "content": body_text,
        "components": json.dumps(components_preview), "user_id": u_id, "last_synced": utc_now
    })

    return {"message": "OTP Template submitted to Meta. It will appear as PENDING until approved."}

@app.get("/api/debug/webhooks")
async def get_webhook_debug_logs(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    db = await get_db()
    # ENSURE TABLE EXISTS (Fixes 500 error on fresh DBs)
    try:
        await db.execute("CREATE TABLE IF NOT EXISTS webhook_logs (id INTEGER PRIMARY KEY AUTO_INCREMENT, payload TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    except:
        # Fallback for SQLite
        try: await db.execute("CREATE TABLE IF NOT EXISTS webhook_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
        except: pass
        
    try:
        rows = await db.fetch_all("SELECT * FROM webhook_logs ORDER BY id DESC LIMIT 20")
        return safe_json_response([dict(r) for r in rows])
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    # Listen on 0.0.0.0 for cloud, but 127.0.0.1 is fine for local
    host = "127.0.0.1" if not os.environ.get('PORT') else "0.0.0.0"
    
    # Auto-open browser when running locally
    if not os.environ.get('PORT'):
        try:
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{port}")
        except:
            pass

    uvicorn.run(app, host=host, port=port)
