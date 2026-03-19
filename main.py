from fastapi import FastAPI, UploadFile, Form, Request, BackgroundTasks
import re, os
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import asyncio
import json
import random
import webbrowser
import requests
from contextlib import asynccontextmanager
from database import init_db, get_db
from utils import extract_phone_numbers, substitute_template, sync_to_google_sheet, send_email_report, get_now_ist
from whatsapp_service import send_whatsapp_message, get_whatsapp_templates, create_whatsapp_template

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

async def get_active_credentials():
    db = await get_db()
    async with db.execute("SELECT whatsapp_token as token, phone_number_id as phone_id, waba_id FROM user_credentials WHERE is_active = 1 ORDER BY last_updated DESC LIMIT 1") as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    # Auto-open browser (local only)
    if not os.environ.get('PORT'):
        url = "http://127.0.0.1:8000"
        webbrowser.open(url)
    yield
    # Shutdown logic

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# SSE event queues for real-time updates
event_queues = []

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

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = await get_db()
    
    # Get linked account info
    async with db.execute("SELECT phone_number FROM user_credentials WHERE is_active = 1 LIMIT 1") as cursor:
        cred = await cursor.fetchone()
        linked_phone = cred['phone_number'] if cred else None

    async with db.execute("SELECT * FROM campaigns ORDER BY timestamp DESC LIMIT 50") as cursor:
        campaigns = await cursor.fetchall()
    
    async with db.execute("SELECT * FROM templates ORDER BY name ASC") as cursor:
        templates_list = await cursor.fetchall()
        
    await db.close()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "campaigns": campaigns,
        "templates": templates_list,
        "fb_app_id": FB_APP_ID,
        "fb_config_id": FB_CONFIG_ID,
        "linked_phone": linked_phone
    })

async def process_campaign(campaign_id: int, data: list, phone_col: str, message_template: str, msg_type: str = "text", template_name: str = "", language_code: str = "en_US", report_email: str = None):
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
        phone = str(row.get(phone_col, ""))
        if not phone or str(phone).lower() == 'nan':
            continue
            
        # Handle templates vs plain text
        if msg_type == "template":
            # Extract placeholders in order for template parameters
            # Regex for [var], {var}, {{var}}, (var)
            patterns = [r'\{\{(.*?)\}\}', r'\{(.*?)\}', r'\[(.*?)\]', r'\((.*?)\)']
            placeholders = []
            for pat in patterns:
                found = re.findall(pat, message_template)
                if found: # Take the first matching pattern style found in the string
                    placeholders = [p.strip().lower() for p in found]
                    break
            
            # Map values from row
            normalized_row = {str(k).strip().lower(): v for k, v in row.items()}
            message_to_send = [str(normalized_row.get(p, "")) for p in placeholders]
            # Log what we're sending as params
            print(f"DEBUG: Template params for {phone}: {message_to_send}")
        else:
            message_to_send = substitute_template(message_template, row)
        
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
        success, error = await send_whatsapp_message(phone, message_to_send, msg_type, template_name, language_code, credentials=credentials)
        
        status = "Success" if success else "Failed"
        is_auth_error = False
        if not success:
            failed_count += 1
            if "401" in str(error) or "any_other_auth_indicator" in str(error):
                is_auth_error = True
        else:
            success_count += 1
            
        # Log message status with IST
        now_ist = get_now_ist()
        await db.execute("""
            INSERT INTO messages (campaign_id, phone, message, status, error_message, row_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (campaign_id, phone, str(message_to_send), status, error, json.dumps(row), now_ist))
        
        # Update campaign progress
        await db.execute("""
            UPDATE campaigns 
            SET sent_success = ?, sent_failed = ?, status = 'Processing'
            WHERE id = ?
        """, (success_count, failed_count, campaign_id))
        await db.commit()
        
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

    # Update final campaign status and counts (Safety sync)
    await db.execute("""
        UPDATE campaigns 
        SET sent_success = ?, sent_failed = ?, status = 'Completed' 
        WHERE id = ?
    """, (success_count, failed_count, campaign_id))
    await db.commit()
    
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
    async with db.execute("SELECT row_data, status, timestamp FROM messages WHERE campaign_id = ?", (campaign_id,)) as cursor:
        msg_rows = await cursor.fetchall()
        for r in msg_rows:
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
        
        await db.close()

@app.post("/clear-history")
async def clear_history():
    db = await get_db()
    # Delete messages first due to FK, then campaigns
    await db.execute("DELETE FROM messages")
    await db.execute("DELETE FROM campaigns")
    await db.commit()
    await db.close()
    return {"message": "History cleared"}

@app.get("/export/{campaign_id}")
async def export_campaign(campaign_id: int):
    import pandas as pd
    import io
    from fastapi.responses import StreamingResponse

    db = await get_db()
    async with db.execute("""
        SELECT row_data, status, timestamp, phone 
        FROM messages 
        WHERE campaign_id = ?
    """, (campaign_id,)) as cursor:
        rows = await cursor.fetchall()
    await db.close()

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
    await db.commit()
    await db.close()
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
        VALUES (?, ?, ?, ?, 1)
    """, (access_token, phone_id, waba_id, phone_number))
    await db.commit()
    await db.close()
    
    return {"message": "WhatsApp Account linked successfully!", "phone": phone_number}

@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    message: str = Form(...),
    msg_type: str = Form("text"),
    template_name: str = Form(None),
    language_code: str = Form("en_US"),
    report_email: str = Form(None)
):
    content = await file.read()
    try:
        data, phone_col = extract_phone_numbers(content, file.filename)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    db = await get_db()
    
    # Use IST for campaign creation
    now_ist = get_now_ist()
    filename = file.filename
    await db.execute("""
        INSERT INTO campaigns (name, total_numbers, status, timestamp) 
        VALUES (?, ?, ?, ?)
    """, (filename, len(data), 'Processing', now_ist))
    await db.commit()
    
    async with db.execute("SELECT last_insert_rowid()") as cursor:
        campaign_id = (await cursor.fetchone())[0]
        
    # Also prepare the report_data header with the correct timestamp if needed
    # but the individual message timestamps are more important
    await db.close()

    background_tasks.add_task(
        process_campaign, 
        campaign_id, 
        data, 
        phone_col, 
        message, 
        msg_type, 
        template_name, 
        language_code,
        report_email
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
    async with db.execute("SELECT * FROM templates") as cursor:
        rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]

@app.post("/templates/sync")
async def sync_templates():
    credentials = await get_active_credentials()
    if not credentials:
        print("DEBUG: No active credentials found for sync")
        return JSONResponse(status_code=400, content={"error": "Please link your WhatsApp account first. No active credentials found."})
    
    print(f"DEBUG: Syncing templates for WABA: {credentials.get('waba_id')}")
    templates_data = get_whatsapp_templates(credentials=credentials)
    
    if not templates_data:
        # If the list is empty, it could be no templates OR an error.
        # But we added logging inside get_whatsapp_templates
        return JSONResponse(status_code=400, content={"error": "Failed to sync templates from Meta. Check server logs for details."})

    db = await get_db()
    sync_count = 0
    for t in templates_data:
        name = t.get('name')
        category = t.get('category')
        language = t.get('language')
        status = t.get('status')
        
        content = ""
        for comp in t.get('components', []):
            if comp.get('type') == 'BODY':
                content = comp.get('text', '')
                break
        
        await db.execute("""
            INSERT INTO templates (name, category, language, status, content, last_synced)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                status = excluded.status,
                content = excluded.content,
                last_synced = CURRENT_TIMESTAMP
        """, (name, category, language, status, content))
        sync_count += 1
    
    await db.commit()
    await db.close()
    return {"message": f"Synced {sync_count} templates from Meta"}

@app.post("/create-template")
async def create_template_route(
    name: str = Form(...),
    category: str = Form("MARKETING"),
    language: str = Form("en_US"),
    content: str = Form(...)
):
    credentials = await get_active_credentials()
    success, error_msg = create_whatsapp_template(name, category, language, content, credentials=credentials)
    if not success:
        return JSONResponse(status_code=400, content={"error": error_msg})
    
    db = await get_db()
    await db.execute("""
        INSERT INTO templates (name, category, language, status, content)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            status = 'PENDING',
            content = excluded.content
    """, (name, category, language, 'PENDING', content))
    await db.commit()
    await db.close()
    return {"message": "Template created and submitted to Meta for approval"}

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return """
    <html>
        <head><title>Privacy Policy - BulkPulse</title></head>
        <body style="font-family: sans-serif; padding: 40px; max-width: 800px; margin: auto; line-height: 1.6;">
            <h1>Privacy Policy</h1>
            <p><strong>Effective Date: March 19, 2026</strong></p>
            <p>BulkPulse ("this tool") is developed by Bitbinders. This Privacy Policy describes how we handle information when you use our WhatsApp messaging service.</p>
            <h2>1. Information We Collect</h2>
            <p>We only collect the WhatsApp Business Account ID and Phone Number ID that you explicitly link via Facebook Login. We do not store your personal Facebook password or messages.</p>
            <h2>2. How We Use Information</h2>
            <p>We use this information solely to send messages on your behalf via the WhatsApp Business API as requested by you within the tool dashboard.</p>
            <h2>3. Data Sharing</h2>
            <p>We do not share your WhatsApp data with any third parties except for Meta (Facebook) as required to process your API requests.</p>
            <h2>4. Your Rights</h2>
            <p>You can unlink your WhatsApp account at any time from the dashboard, which will immediately stop our access to your account.</p>
            <p>For more details, contact info@bitbinders.in</p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    # Listen on 0.0.0.0 for cloud, but 127.0.0.1 is fine for local
    host = "127.0.0.1" if not os.environ.get('PORT') else "0.0.0.0"
    uvicorn.run(app, host=host, port=port)
