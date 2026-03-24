from fastapi import FastAPI, UploadFile, Form, Request, BackgroundTasks, File
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
from whatsapp_service import send_whatsapp_message, get_whatsapp_templates, create_whatsapp_template, fetch_meta_templates, delete_whatsapp_template, upload_whatsapp_media
import datetime

# Settings
USE_REAL_API = True # Set to False for local testing without sending real messages

# Meta App Credentials (for Token Exchange)
# The user should configure these in their Meta App Dashboard
FB_APP_ID = "916270141105838" 
FB_APP_SECRET = "3f58694b5b0ec480d6992dabc16e6ece"
FB_CONFIG_ID = "1819547065399749" # Configuration ID for Business Login

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

async def get_active_credentials():
    db = await get_db()
    row = await db.fetch_one("SELECT whatsapp_token as token, phone_number_id as phone_id, waba_id FROM user_credentials WHERE is_active = 1 ORDER BY last_updated DESC LIMIT 1")
    return dict(row) if row else None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        print("DEBUG: Initializing database...")
        await init_db()
        print("DEBUG: Database initialized successfully.")
    except Exception as e:
        print(f"DEBUG: Error during database init: {str(e)}")
        
    yield
    # Shutdown logic

app = FastAPI(lifespan=lifespan)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# SSE event queues for real-time updates
event_queues = []

# Media Upload Directory — use /tmp on Vercel (read-only filesystem), fallback to static/uploads locally
UPLOAD_DIR = "/tmp/uploads" if os.environ.get("VERCEL") else os.path.join(os.getcwd(), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload-media")
async def upload_media(file: UploadFile = File(...)):
    try:
        ext = os.path.splitext(file.filename)[1]
        unique_name = f"sample_{random.randint(1000, 9999)}_{int(asyncio.get_event_loop().time())}{ext}"
        save_path = os.path.join(UPLOAD_DIR, unique_name)
        
        with open(save_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        url = f"/static/uploads/{unique_name}"
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

async def get_dashboard_stats():
    db = await get_db()
    
    # IST Offset Helper (Manual for consistency)
    ist_delta = datetime.timedelta(hours=5, minutes=30)
    now_ist = datetime.datetime.now(datetime.timezone(ist_delta))
    
    # Today Start (Local IST)
    today_start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    # Convert back to UTC for DB queries
    today_str = today_start_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    # Last 7 days
    seven_days_ago_ist = today_start_ist - datetime.timedelta(days=7)
    seven_days_str = seven_days_ago_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    # Total Templates & Approved
    total_t = await db.fetch_one("SELECT COUNT(*) as count FROM templates")
    approved_t = await db.fetch_one("SELECT COUNT(*) as count FROM templates WHERE status = 'APPROVED'")

    # Incoming (today & 7 days)
    inc_today = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE direction='inbound' AND timestamp >= :ts", {"ts": today_str})
    inc_7d = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE direction='inbound' AND timestamp >= :ts", {"ts": seven_days_str})

    # Outgoing (today & 7 days)
    chat_out_today = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE direction='outbound' AND timestamp >= :ts", {"ts": today_str})
    chat_out_7d = await db.fetch_one("SELECT COUNT(*) as count FROM chat_messages WHERE direction='outbound' AND timestamp >= :ts", {"ts": seven_days_str})
    
    camp_out_today = await db.fetch_one("SELECT COUNT(*) as count FROM messages WHERE timestamp >= :ts", {"ts": today_str})
    camp_out_7d = await db.fetch_one("SELECT COUNT(*) as count FROM messages WHERE timestamp >= :ts", {"ts": seven_days_str})
    
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
    db = await get_db()
    
    # Get linked account info
    cred = await db.fetch_one("SELECT phone_number FROM user_credentials WHERE is_active = 1 LIMIT 1")
    linked_phone = cred['phone_number'] if cred else None

    campaigns = await db.fetch_all("SELECT * FROM campaigns ORDER BY timestamp DESC LIMIT 50")
    
    templates_raw = await db.fetch_all("SELECT * FROM templates ORDER BY name ASC")
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
        "stats": await get_dashboard_stats()
    })

@app.get("/api/templates")
async def api_get_templates():
    db = await get_db()
    templates_raw = await db.fetch_all("SELECT * FROM templates ORDER BY name ASC")
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

async def process_campaign(campaign_id: int, data: list, phone_col: str, message_template: str, msg_type: str = "text", template_name: str = "", language_code: str = "en_US", report_email: str = None, mappings: dict = None):
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
    
    for i, row in enumerate(data):
        raw_phone = str(row.get(phone_col, ""))
        phone = normalize_phone(raw_phone)
        if not phone:
            continue
            
        media_url = None
        template_params = []
        message_to_send = ""

        # Handle templates vs plain text
        if msg_type == "template":
            message_to_send = message_template or f"Template: {template_name}"
            if mappings:
                # 1. Header Mapping
                if mappings.get('header'):
                    media_url = row.get(mappings['header'])
                
                # 2. Variable Mappings (vars: {"1": "col_a", "2": "col_b"})
                vars_map = mappings.get('vars', {})
                # Sort by numeric key to ensure {{1}}, {{2}} order
                sorted_keys = sorted(vars_map.keys(), key=lambda x: int(x))
                for idx, k in enumerate(sorted_keys):
                    col_name = vars_map[k]
                    val = row.get(col_name, "")
                    template_params.append(str(val))
                    # Substitute variable into text log for Chat UI
                    pattern = r'\{\{\s*' + re.escape(str(idx + 1)) + r'\s*\}\}'
                    message_to_send = re.sub(pattern, str(val), message_to_send, flags=re.IGNORECASE)
            else:
                # Fallback for simple templates (auto-detection) - Keep for backward compatibility
                patterns = [r'\{\{(.*?)\}\}', r'\{(.*?)\}', r'\[(.*?)\]', r'\((.*?)\)']
                placeholders = []
                for pat in patterns:
                    found = re.findall(pat, message_template or "")
                    if found:
                        placeholders = [p.strip().lower() for p in found]
                        break
                normalized_row = {str(k).strip().lower(): v for k, v in row.items()}
                template_params = [str(normalized_row.get(p, "")) for p in placeholders]
                # Substitute variable into text log for Chat UI
                for p in placeholders:
                    val = str(normalized_row.get(p, ""))
                    message_to_send = re.sub(r'\{\{\s*' + re.escape(p) + r'\s*\}\}', val, message_to_send, flags=re.IGNORECASE)
            
            print(f"DEBUG: Template params for {phone}: {template_params}, Media: {media_url}")
        else:
            message_to_send = substitute_template(message_template or "", row)
        
        # Human mimicry delay
        delay = random.randint(10, 35) if USE_REAL_API else random.randint(1, 2)
        
        # Batching break
        if USE_REAL_API and i > 0 and i % 5 == 0:
            batch_break = random.randint(60, 120)
            break_event = json.dumps({
                "campaign_id": campaign_id,
                "status_text": f"Taking a human break ({batch_break}s)...",
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
        
        credentials = await get_active_credentials()
        success, response = await send_whatsapp_message(
            phone, message_to_send, msg_type, template_name, language_code, 
            media_url=media_url, template_params=template_params, credentials=credentials
        )
        
        if not success:
            print(f"DEBUG ERROR: Campaign Message Failed to {phone}. Response: {response}")
            failed_count += 1
        else:
            success_count += 1
        
        status = "sent" if success else "failed"
        error = ""
        wa_message_id = None
        
        if success:
            success_count += 1
            # Extract message ID from Meta response
            # Response is usually {'messaging_product': 'whatsapp', 'contacts': [...], 'messages': [{'id': '...'}]}
            if isinstance(response, dict) and 'messages' in response:
                wa_message_id = response['messages'][0].get('id')
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
            INSERT INTO messages (campaign_id, phone, message, status, error_message, whatsapp_message_id, row_data, timestamp)
            VALUES (:campaign_id, :phone, :message, :status, :error_message, :wa_id, :row_data, :timestamp)
        """, {
            "campaign_id": campaign_id, "phone": phone, "message": str(message_to_send), 
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
async def facebook_unlink():
    db = await get_db()
    # Deactivate all credentials
    await db.execute("UPDATE user_credentials SET is_active = 0")
    return {"message": "WhatsApp unlinked successfully"}

@app.post("/auth/facebook/callback")
async def facebook_auth_callback(request: Request, data: dict):
    code = data.get('code')
    access_token = data.get('access_token')
    
    # 0. Exchange code for access_token if needed (Security Upgrade)
    if code and not access_token:
        try:
            # Reconstruct the origin from headers
            proto = request.headers.get('x-forwarded-proto', 'https') 
            host = request.headers.get('x-forwarded-host') or request.headers.get('host') or "127.0.0.1:8000"
            origin = f"{proto}://{host}"
            referer = request.headers.get('referer', '').split('?')[0].split('#')[0]

            redirect_uris = [origin.rstrip('/') + '/', origin.rstrip('/'), referer.rstrip('/') + '/', referer.rstrip('/'), ""]
            
            for r_uri in redirect_uris:
                exchange_url = "https://graph.facebook.com/v21.0/oauth/access_token"
                data_payload = {"client_id": FB_APP_ID, "client_secret": FB_APP_SECRET, "code": code}
                if r_uri: data_payload["redirect_uri"] = r_uri
                
                res = requests.post(exchange_url, data=data_payload)
                res_json = res.json()
                if "access_token" in res_json:
                    access_token = res_json["access_token"]
                    break

        except Exception as e:
            print(f"ERROR FB: Token exchange exception: {str(e)}")

    if not access_token:
        return JSONResponse({"error": "No access token or valid code provided"}, status_code=400)
    
    waba_id = data.get('waba_id')
    phone_id = data.get('phone_id')

    # Auto-detection if requested
    if waba_id == "AUTO_DETECT" or phone_id == "AUTO_DETECT":
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 1. Get WhatsApp Business Accounts
            waba_url = f"https://graph.facebook.com/v21.0/me/whatsapp_business_accounts"
            waba_res = requests.get(waba_url, headers=headers)
            waba_json = waba_res.json()
            waba_data = waba_json.get('data', [])
            
            print(f"DEBUG FB: WABA Check Response: {waba_json}")
            
            if not waba_data:
                # Fallback: Check debug_token for granular scopes (common for Test Accounts)
                debug_url = f"https://graph.facebook.com/v21.0/debug_token?input_token={access_token}&access_token={FB_APP_ID}|{FB_APP_SECRET}"
                debug_data = requests.get(debug_url).json().get('data', {})
                print(f"DEBUG FB: Fallback Debug Info: {debug_data}")
                
                granular = debug_data.get('granular_scopes', [])
                for scope_item in granular:
                    if scope_item.get('scope') in ['whatsapp_business_management', 'whatsapp_business_messaging']:
                        target_ids = scope_item.get('target_ids', [])
                        if target_ids:
                            # If multiple, prioritize one that might be a 'test' one if we can tell, 
                            # otherwise pick first. Meta doesn't explicitly flag 'Test' in ID, 
                            # but usually the user selects it in the popup.
                            waba_id = target_ids[0]
                            print(f"DEBUG FB: Found WABA ID in granular scopes: {waba_id}")
                            break
                
                if not waba_id or waba_id == "AUTO_DETECT":
                    return JSONResponse({
                        "error": "No WhatsApp Business Accounts found.", 
                        "details": "Meta returned an empty account list. Ensure your WhatsApp account is fully set up.",
                        "meta_response": waba_json
                    }, status_code=404)
            else:
                # If multiple WABAs, try to find one that says 'Test' in its name if possible
                # (Standard detection usually only returns what the user selected)
                waba_id = waba_data[0]['id']
                for w in waba_data:
                    if "test" in w.get('name', '').lower():
                        waba_id = w['id']
                        break
                print(f"DEBUG FB: Selected WABA ID: {waba_id}")
            
            # 2. Get Phone Numbers for this WABA
            phone_url = f"https://graph.facebook.com/v21.0/{waba_id}/phone_numbers"
            phone_res = requests.get(phone_url, headers=headers)
            phone_json = phone_res.json()
            phone_data = phone_json.get('data', [])
            
            print(f"DEBUG FB: Phone Check Response: {phone_json}")
            
            if not phone_data:
                return JSONResponse({
                    "error": "No phone numbers found.", 
                    "details": f"Found WABA {waba_id} but it has no phone numbers linked.",
                    "meta_response": phone_json
                }, status_code=404)
            
            # Prioritize Test Number if available
            phone_id = phone_data[0]['id']
            phone_number = phone_data[0].get('display_phone_number', 'Linked Account')
            
            for p in phone_data:
                if "test" in p.get('display_phone_number', '').lower() or "test" in p.get('verified_name', '').lower():
                    phone_id = p['id']
                    phone_number = p.get('display_phone_number', 'Test Number')
                    break
                    
            print(f"DEBUG FB: Selected Phone ID: {phone_id} ({phone_number})")
            
        except Exception as e:
            print(f"DEBUG FB: Exception during detection: {str(e)}")
            return JSONResponse({"error": f"Auto-detection failed: {str(e)}"}, status_code=500)
    else:
        phone_number = "Custom Account"

    db = await get_db()
    # Deactivate other credentials
    await db.execute("UPDATE user_credentials SET is_active = 0")
    # Save new credentials
    await db.execute("""
        INSERT INTO user_credentials (whatsapp_token, phone_number_id, waba_id, phone_number, is_active)
        VALUES (:token, :phone_id, :waba_id, :phone, 1)
    """, {"token": access_token, "phone_id": phone_id, "waba_id": waba_id, "phone": phone_number})
    
    return {"message": "WhatsApp Account linked successfully!", "phone": phone_number}

@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    single_mobile: str = Form(None),
    message: str = Form(None),
    msg_type: str = Form("text"),
    template_name: str = Form(None),
    language_code: str = Form("en_US"),
    report_email: str = Form(None),
    mappings: str = Form(None)
):
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
        
    db = await get_db()
    now_utc = get_now_utc()
    
    campaign_id = await db.execute("""
        INSERT INTO campaigns (name, total_numbers, status, timestamp) 
        VALUES (:name, :total, :status, :ts)
    """, {"name": filename, "total": len(data), "status": 'Processing', "ts": now_utc})

    background_tasks.add_task(
        process_campaign, 
        campaign_id, 
        data, 
        phone_col, 
        message, 
        msg_type, 
        template_name, 
        language_code,
        report_email,
        mappings=mappings_dict
    )
    
    return {"message": "Campaign started", "campaign_id": campaign_id, "total": len(data)}

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
async def get_templates_route():
    db = await get_db()
    rows = await db.fetch_all("SELECT * FROM templates")
    return [dict(r) for r in rows]

@app.post("/templates/sync")
@app.post("/api/templates/sync")
async def sync_templates():
    credentials = await get_active_credentials()
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
    is_mysql = "mysql" in db.url.scheme
    sync_count = 0
    for t in templates_data:
        name = t.get('name')
        category = t.get('category')
        language = t.get('language')
        status = t.get('status')
        content = t.get('content')
        components = t.get('components')
        
        utc_now = get_now_utc()
        if is_mysql:
            query = """
                INSERT INTO templates (name, category, language, status, content, components, last_synced)
                VALUES (:name, :category, :language, :status, :content, :components, :last_synced)
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    content = VALUES(content),
                    components = VALUES(components),
                    last_synced = VALUES(last_synced)
            """
        else:
            query = """
                INSERT INTO templates (name, category, language, status, content, components, last_synced)
                VALUES (:name, :category, :language, :status, :content, :components, :last_synced)
                ON CONFLICT(name) DO UPDATE SET
                    status = excluded.status,
                    content = excluded.content,
                    components = excluded.components,
                    last_synced = :last_synced
            """
            
        await db.execute(query, {
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
async def delete_template_api(name: str = Form(...)):
    credentials = await get_active_credentials()
    db = await get_db()
    
    # 1. Attempt to delete from Meta
    try:
        success, msg = await delete_whatsapp_template(name, credentials)
        print(f"DEBUG: Meta delete response for {name}: {success}, {msg}")
    except Exception as e:
        print(f"ERROR: Exception during Meta delete: {e}")
    
    # 2. Always delete locally to keep UI clean
    await db.execute("DELETE FROM templates WHERE name = :name", {"name": name})
    
    return {"message": "Template deleted successfully"}

@app.post("/api/templates/create-complex")
async def create_complex_template(
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
    credentials = await get_active_credentials()
    
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
            # Use provided URL or a placeholder if empty
            media_url = h_text if (h_text and h_text.startswith('http')) else "https://www.bitbinders.in/sample-media.jpg"
            components.append({
                "type": "HEADER", 
                "format": header_type, 
                "example": {"link": [media_url]}
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
    
    # Save to Local DB
    db = await get_db()
    is_mysql = "mysql" in db.url.scheme
    
    utc_now = get_now_utc()
    if is_mysql:
        query = """
            INSERT INTO templates (name, category, language, status, content, components, variable_map, last_synced)
            VALUES (:name, :category, :language, :status, :content, :components, :var_map, :last_synced)
            ON DUPLICATE KEY UPDATE
                category = VALUES(category),
                language = VALUES(language),
                status = 'PENDING',
                content = VALUES(content),
                components = VALUES(components),
                variable_map = VALUES(variable_map),
                last_synced = VALUES(last_synced)
        """
    else:
        query = """
            INSERT INTO templates (name, category, language, status, content, components, variable_map, last_synced)
            VALUES (:name, :category, :language, :status, :content, :components, :var_map, :last_synced)
            ON CONFLICT(name) DO UPDATE SET
                category = excluded.category,
                language = excluded.language,
                status = 'PENDING',
                content = excluded.content,
                components = excluded.components,
                variable_map = excluded.variable_map,
                last_synced = :last_synced
        """

    await db.execute(query, {
        "name": name, "category": category, "language": language, 
        "status": 'PENDING', "content": content, "components": json.dumps(components), 
        "var_map": variable_map, "last_synced": utc_now
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
    return [dict(r) for r in rows]

@app.get("/api/history")
async def get_history():
    db = await get_db()
    # Calculate all stats dynamically for consistency
    rows = await db.fetch_all("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM messages WHERE campaign_id = c.id AND (status = 'sent' OR status = 'delivered' OR status = 'read')) as sent_success,
               (SELECT COUNT(*) FROM messages WHERE campaign_id = c.id AND status = 'delivered') as delivered,
               (SELECT COUNT(*) FROM messages WHERE campaign_id = c.id AND status = 'read') as read,
               (SELECT COUNT(*) FROM messages WHERE campaign_id = c.id AND status = 'failed') as failed
        FROM campaigns c 
        ORDER BY timestamp DESC
    """)
    return safe_json_response([dict(r) for r in rows])

@app.get("/api/campaign/{campaign_id}/details")
async def get_campaign_details(campaign_id: int):
    db = await get_db()
    # Summary stats
    stats = await db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
            SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered,
            SUM(CASE WHEN status = 'read' THEN 1 ELSE 0 END) as read,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM messages WHERE campaign_id = :id
    """, {"id": campaign_id})
    
    # Message list
    messages = await db.fetch_all("""
        SELECT phone, status, error_message, timestamp 
        FROM messages 
        WHERE campaign_id = :id
        ORDER BY timestamp ASC
    """, {"id": campaign_id})
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
    print(f"DEBUG WEBHOOK: Received update: {json.dumps(data)}")

    # Check if it's a WhatsApp status update
    try:
        entries = data.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                statuses = value.get("statuses", [])
                
                for status_update in statuses:
                    wa_message_id = status_update.get("id")
                    new_status = status_update.get("status") # sent, delivered, read, failed
                    
                    db = await get_db()
                    # Check if message exists
                    msg = await db.fetch_one("SELECT campaign_id FROM messages WHERE whatsapp_message_id = :id", {"id": wa_message_id})
                    if msg:
                        campaign_id = msg['campaign_id']
                        print(f"DEBUG WEBHOOK: Updating message {wa_message_id} to {new_status}")
                        
                        # Update message status and error message if failed
                        error_msg = None
                        if new_status == 'failed':
                            errors = status_update.get("errors", [])
                            if errors:
                                error_msg = errors[0].get("message", "Unknown Meta Error")
                        
                        if error_msg:
                            await db.execute("""
                                UPDATE messages SET status = :status, error_message = :err WHERE whatsapp_message_id = :id
                            """, {"status": new_status, "err": error_msg, "id": wa_message_id})
                        else:
                            await db.execute("""
                                UPDATE messages SET status = :status WHERE whatsapp_message_id = :id
                            """, {"status": new_status, "id": wa_message_id})
                    else:
                        print(f"DEBUG WEBHOOK: Message ID {wa_message_id} not found in DB")
                # Check if it's an incoming message
                incoming_messages = value.get("messages", [])
                for msg_data in incoming_messages:
                    wa_message_id = msg_data.get("id")
                    from_phone = msg_data.get("from")
                    msg_type = msg_data.get("type")
                    
                    if msg_type == "text":
                        body = msg_data.get("text", {}).get("body")
                        db = await get_db()
                        # Avoid duplicates
                        existing = await db.fetch_one("SELECT id FROM chat_messages WHERE wa_message_id = :id", {"id": wa_message_id})
                        if not existing:
                            clean_from = normalize_phone(from_phone)
                            await db.execute("""
                                INSERT INTO chat_messages (phone, message, direction, wa_message_id, timestamp)
                                VALUES (:phone, :message, 'inbound', :id, :ts)
                            """, {"phone": clean_from, "message": body, "id": wa_message_id, "ts": get_now_utc()})
                            print(f"DEBUG WEBHOOK: Saved inbound message from {clean_from}")
                
    except Exception as e:
        print(f"DEBUG WEBHOOK: Error processing: {str(e)}")

    return {"status": "ok"}

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
    return [dict(r) for r in rows]

@app.get("/api/chat/contacts")
async def get_chat_contacts():
    db = await get_db()
    # Unique phones and their unread status
    rows = await db.fetch_all("""
        SELECT t.phone, 
               MAX(CASE WHEN c.is_read = 0 AND c.direction = 'inbound' THEN 1 ELSE 0 END) as has_unread
        FROM (
            SELECT phone FROM messages WHERE status IN ('sent', 'delivered', 'read')
            UNION
            SELECT phone FROM chat_messages
        ) t
        LEFT JOIN chat_messages c ON t.phone = c.phone
        WHERE t.phone IS NOT NULL AND t.phone != ''
        GROUP BY t.phone
        ORDER BY MAX(c.timestamp) DESC, t.phone ASC
    """)
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
    name: str = Form(...),
    category: str = Form(...),
    body_text: str = Form(...),
    components_json: Optional[str] = Form(None)
):
    """Updates an existing WhatsApp template."""
    import json
    from whatsapp_service import update_whatsapp_template
    
    credentials = await get_active_credentials()
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
async def get_chat_history(phone: str):
    db = await get_db()
    # Bi-directional history
    # We include messages from 'messages' table (campaigns) and 'chat_messages' (interactive)
    rows = await db.fetch_all("""
        SELECT 'outbound' as direction, message, timestamp, status as wa_status, NULL as wa_message_id
        FROM messages 
        WHERE phone = :p AND status != 'failed'
        UNION ALL
        SELECT direction, message, timestamp, NULL as wa_status, wa_message_id
        FROM chat_messages
        WHERE phone = :p
        ORDER BY timestamp ASC
    """, {"p": phone})
    
    return [dict(r) for r in rows]

@app.post("/api/chat/send")
async def send_chat_reply(
    phone: str = Form(...),
    message: str = Form(""),
    file: UploadFile = File(None),
    template_name: str = Form(None),
    msg_type: str = Form("text")
):
    if not phone:
        return JSONResponse(status_code=400, content={"error": "Phone number is required"})
    
    phone = normalize_phone(phone)
    
    if not message and not file and not template_name:
        return JSONResponse(status_code=400, content={"error": "Message, file, or template is required"})

    # Get Credentials
    db = await get_db()
    acc = await db.fetch_one("SELECT whatsapp_token, phone_number_id, waba_id FROM user_credentials WHERE is_active = 1 ORDER BY last_updated DESC LIMIT 1")
    if not acc:
        return JSONResponse(status_code=400, content={"error": "No WhatsApp account linked"})
    
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
        credentials=credentials
    )
    
    if success:
        wa_id = None
        if isinstance(response, dict) and "messages" in response:
            wa_id = response["messages"][0].get("id")
            
        # Save to Chat History
        await db.execute("""
            INSERT INTO chat_messages (phone, message, direction, wa_message_id, is_read, timestamp)
            VALUES (:phone, :message, 'outbound', :id, 1, :ts)
        """, {"phone": phone, "message": display_message, "id": wa_id, "ts": get_now_utc()})
        
        return {"status": "ok", "wa_id": wa_id}
    else:
        return JSONResponse(status_code=400, content={"error": f"WhatsApp Error: {str(response)}"})

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
async def update_template_json(req: TemplateFormJSONReq):
    credentials = await get_active_credentials()
    
    success, error_msg = update_whatsapp_template(
        name=req.name, 
        category=req.category, 
        components=[c.dict(exclude_none=True) for c in req.components], 
        credentials=credentials
    )
    
    if not success:
        return JSONResponse(status_code=400, content={"error": error_msg})
        
    return {"message": "Template updated successfully on Meta."}

@app.post("/api/templates/create")
async def create_template_json(req: TemplateFormJSONReq):
    credentials = await get_active_credentials()
    
    success, error_msg = create_whatsapp_template(
        name=req.name, 
        category=req.category,
        language=req.language,
        components=[c.dict(exclude_none=True) for c in req.components], 
        credentials=credentials
    )
    
    if not success:
        return JSONResponse(status_code=400, content={"error": error_msg})
        
    return {"message": "Template created successfully on Meta."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    # Listen on 0.0.0.0 for cloud, but 127.0.0.1 is fine for local
    host = "127.0.0.1" if not os.environ.get('PORT') else "0.0.0.0"
    uvicorn.run(app, host=host, port=port)
