import json
from datetime import datetime, timedelta, timezone
from database import get_db
from whatsapp_service import send_whatsapp_message
import asyncio
import httpx

async def log_bot_reply(user_id, phone, text, wamid=""):
    db = await get_db()
    ts = datetime.now(timezone.utc)
    try:
        await db.execute("""
            INSERT INTO chat_messages (user_id, phone, message, direction, wa_message_id, is_read, timestamp, sender_name, status)
            VALUES (:u, :phone, :msg, 'outbound', :wamid, 1, :ts, 'Bot', 'sent')
        """, {"u": user_id, "phone": phone, "msg": text, "wamid": wamid, "ts": ts})
    except Exception as e:
        print(f"DEBUG: Failed to save bot reply to chat_messages: {e}")

async def get_active_credentials(user_id: int):
    db = await get_db()
    return await db.fetch_one("SELECT whatsapp_token, phone_number_id, waba_id, phone_number FROM user_credentials WHERE is_active = 1 AND user_id = :u LIMIT 1", {"u": user_id})

def get_node_outputs(node):
    # Returns a list of next node IDs
    outputs = []
    outs = node.get('outputs', {})
    for out_key, out_val in outs.items():
        conns = out_val.get('connections', [])
        for conn in conns:
            outputs.append({
                'output_key': out_key,
                'target_node': str(conn.get('node'))
            })
    return outputs

async def process_chatbot_message(user_id: int, phone: str, body: str, msg_type: str, raw_payload: dict = None):
    db = await get_db()
    
    # 1. Parse Input
    text_input = ""
    interactive_id = None
    
    if msg_type == "text":
        text_input = str(body).strip().lower()
    elif msg_type == "interactive" and raw_payload:
        # Extract button or list replies
        try:
            inter = raw_payload.get('interactive', {})
            inter_type = inter.get('type')
            if inter_type == 'button_reply':
                interactive_id = inter.get('button_reply', {}).get('id')
                text_input = str(inter.get('button_reply', {}).get('title', '')).strip().lower()
            elif inter_type == 'list_reply':
                interactive_id = inter.get('list_reply', {}).get('id')
                text_input = str(inter.get('list_reply', {}).get('title', '')).strip().lower()
            elif inter_type == 'nfm_reply':
                text_input = "form_submitted"
        except:
            pass
    elif msg_type == "location":
        text_input = "location" # Special keyword we can use

    # 2. Check Triggers First (Global overrides)
    trigger_flow_id = None
    if text_input:
        trigger = await db.fetch_one("SELECT flow_id FROM triggers WHERE user_id = :uid AND LOWER(keyword) = :kw LIMIT 1", {"uid": user_id, "kw": text_input})
        if trigger:
            trigger_flow_id = trigger['flow_id']
            # Clear old session because they triggered a new flow
            await db.execute("DELETE FROM user_sessions WHERE user_id = :uid AND phone_number = :phone", {"uid": user_id, "phone": phone})
            
            flow = await db.fetch_one("SELECT flow_json FROM flows WHERE id = :fid", {"fid": trigger_flow_id})
            if flow:
                try:
                    flow_data = json.loads(flow['flow_json'])
                    nodes_dict = flow_data.get('drawflow', {}).get('Home', {}).get('data', {})
                    
                    start_node = next((n for n in nodes_dict.values() if n.get('data', {}).get('action') == 'start'), None)
                    if start_node:
                        # Insert new session
                        await db.execute("INSERT INTO user_sessions (user_id, phone_number, flow_id, current_node_id, state_data) VALUES (:uid, :phone, :fid, :node, '{}')", {"uid": user_id, "phone": phone, "fid": trigger_flow_id, "node": start_node['id']})
                        session_res = await db.fetch_one("SELECT id FROM user_sessions WHERE phone_number = :p ORDER BY id DESC LIMIT 1", {"p": phone})
                        session_id = session_res['id']
                        
                        outputs = get_node_outputs(start_node)
                        if outputs:
                            await process_node_execution(user_id, phone, outputs[0]['target_node'], nodes_dict, session_id)
                except Exception as e:
                    import traceback
                    print(f"DEBUG: Trigger flow start error:")
                    traceback.print_exc()
            return # Flow started, stop processing here

    # 3. Check Session (if no global trigger matched)
    session = await db.fetch_one("SELECT * FROM user_sessions WHERE user_id = :uid AND phone_number = :phone LIMIT 1", {"uid": user_id, "phone": phone})
    
    now_utc = datetime.now(timezone.utc)
    if session:
        last_interaction = session['last_interaction_at']
        if last_interaction.tzinfo is None:
            last_interaction = last_interaction.replace(tzinfo=timezone.utc)
            
        if (now_utc - last_interaction).total_seconds() > 24 * 3600:
            await db.execute("DELETE FROM user_sessions WHERE id = :id", {"id": session['id']})
            session = None

    if session:
        flow_id = session['flow_id']
        current_node_id = str(session['current_node_id'])
        
        flow = await db.fetch_one("SELECT flow_json FROM flows WHERE id = :fid", {"fid": flow_id})
        if not flow: return
            
        try:
            flow_data = json.loads(flow['flow_json'])
            nodes_dict = flow_data.get('drawflow', {}).get('Home', {}).get('data', {})
        except: return
        
        current_node = nodes_dict.get(current_node_id)
        if not current_node: return
        
        outputs = get_node_outputs(current_node)
        action = current_node.get('data', {}).get('action')
        
        next_node_id = None
        
        # Determine next node based on action and input
        if action in ['text_button', 'media_button', 'text_list']:
            node_data = current_node.get('data', {})
            matched_output_key = None
            
            # Button/Option matching logic
            for key, val in node_data.items():
                if (key.startswith('btn') or key.startswith('opt')) and str(val).strip().lower() == text_input:
                    idx = key.replace('btn', '').replace('opt', '')
                    matched_output_key = f"output_{idx}"
                    break
            
            if matched_output_key:
                for out in outputs:
                    if out['output_key'] == matched_output_key:
                        next_node_id = out['target_node']
                        break
            elif len(outputs) == 1:
                # Fallback to the only output
                next_node_id = outputs[0]['target_node']
                
        else:
            # Fallback or simple text matching
            if len(outputs) == 1:
                next_node_id = outputs[0]['target_node']
                
        if next_node_id:
            await process_node_execution(user_id, phone, next_node_id, nodes_dict, session['id'])


async def process_node_execution(user_id, phone, node_id, nodes_dict, session_id):
    db = await get_db()
    current_id = str(node_id)
    
    while current_id in nodes_dict:
        node = nodes_dict[current_id]
        data = node.get('data', {})
        action = data.get('action')
        
        expects_input = await execute_single_node(user_id, phone, data)
        
        # Update session to currently paused node
        await db.execute("UPDATE user_sessions SET current_node_id = :n, last_interaction_at = CURRENT_TIMESTAMP WHERE id = :id", {"n": current_id, "id": session_id})
        
        if expects_input:
            break
            
        outputs = get_node_outputs(node)
        if not outputs:
            # End of flow
            await db.execute("DELETE FROM user_sessions WHERE id = :id", {"id": session_id})
            break
            
        # Automatically move to next node if it doesn't expect input
        current_id = outputs[0]['target_node']


async def execute_single_node(user_id, phone, node_data):
    """
    Executes the action and returns True if the node expects user input to continue.
    Returns False if execution should flow immediately to the next node.
    """
    action = node_data.get('action')
    credentials_record = await get_active_credentials(user_id)
    if not credentials_record: return False
    credentials = dict(credentials_record)
    
    if action == 'text_reply':
        text = node_data.get('text', '')
        if text:
            success, res = await send_whatsapp_message(phone=phone, message=text, msg_type="text", credentials=credentials)
            if success:
                wamid = res.get('messages', [{}])[0].get('id', '')
                await log_bot_reply(user_id, phone, text, wamid)
            else:
                print(f"DEBUG CHATBOT ERROR: Failed to send text_reply to {phone}: {res}")
        return False
        
    elif action == 'text_button':
        text = node_data.get('text', '')
        buttons = []
        for i in range(1, 10):
            btn_text = node_data.get(f'btn{i}')
            if btn_text:
                buttons.append({
                    "type": "reply",
                    "reply": {"id": f"btn_{i}", "title": str(btn_text)[:20]}
                })
        if text and buttons:
            interactive_obj = {
                "type": "button",
                "body": {"text": text},
                "action": {"buttons": buttons[:3]} # Max 3 buttons
            }
            success, res = await send_whatsapp_message(phone=phone, msg_type="interactive", interactive_obj=interactive_obj, credentials=credentials)
            if success:
                wamid = res.get('messages', [{}])[0].get('id', '')
                await log_bot_reply(user_id, phone, f"[Button Menu sent: {text}]", wamid)
            else:
                print(f"DEBUG CHATBOT ERROR: Failed to send text_button to {phone}: {res}")
        return True # Expects button click
        
    elif action == 'media_button':
        media_url = node_data.get('media_url', '')
        buttons = []
        for i in range(1, 10):
            btn_text = node_data.get(f'btn{i}')
            if btn_text:
                buttons.append({"type": "reply", "reply": {"id": f"btn_{i}", "title": str(btn_text)[:20]}})
        if media_url and buttons:
            fmt = "image"
            if str(media_url).lower().endswith(('.mp4', '.mov')): fmt = "video"
            elif str(media_url).lower().endswith(('.pdf', '.doc', '.docx')): fmt = "document"
            
            interactive_obj = {
                "type": "button",
                "header": {"type": fmt, fmt: {"link": media_url}},
                "body": {"text": "Please select an option:"},
                "action": {"buttons": buttons[:3]}
            }
            success, res = await send_whatsapp_message(phone=phone, msg_type="interactive", interactive_obj=interactive_obj, credentials=credentials)
            if success:
                wamid = res.get('messages', [{}])[0].get('id', '')
                await log_bot_reply(user_id, phone, f"[Media sent with buttons: {media_url}]", wamid)
            else:
                print(f"DEBUG CHATBOT ERROR: Failed to send media_button to {phone}: {res}")
        return True
        
    elif action == 'text_list':
        text = node_data.get('text', '')
        title = node_data.get('list_title', 'Menu')
        rows = []
        for i in range(1, 20):
            opt_text = node_data.get(f'opt{i}')
            if opt_text:
                rows.append({"id": f"opt_{i}", "title": str(opt_text)[:24]})
        if text and rows:
            interactive_obj = {
                "type": "list",
                "body": {"text": text},
                "action": {
                    "button": title[:20],
                    "sections": [{"title": "Options", "rows": rows[:10]}]
                }
            }
            success, res = await send_whatsapp_message(phone=phone, msg_type="interactive", interactive_obj=interactive_obj, credentials=credentials)
            if success:
                wamid = res.get('messages', [{}])[0].get('id', '')
                await log_bot_reply(user_id, phone, f"[List Menu sent: {text}]", wamid)
            else:
                print(f"DEBUG CHATBOT ERROR: Failed to send text_list to {phone}: {res}")
        return True
        
    elif action == 'request_location':
        text = node_data.get('text', 'Please share your location')
        interactive_obj = {
            "type": "location_request_message",
            "body": {"text": text},
            "action": {"name": "send_location"}
        }
        success, res = await send_whatsapp_message(phone=phone, msg_type="interactive", interactive_obj=interactive_obj, credentials=credentials)
        if success:
            wamid = res.get('messages', [{}])[0].get('id', '')
            await log_bot_reply(user_id, phone, f"[Location Request sent: {text}]", wamid)
        else:
            print(f"DEBUG CHATBOT ERROR: Failed to send request_location to {phone}: {res}")
        return True
        
    elif action == 'wapp_form':
        flow_id = node_data.get('flow_id', '').strip()
        flow_cta = node_data.get('flow_cta', 'Open Form').strip()
        if flow_id:
            interactive_obj = {
                "type": "flow",
                "header": {"type": "text", "text": "Form"},
                "body": {"text": "Please tap the button below to fill out the form:"},
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_message_version": "3",
                        "flow_token": f"form_{flow_id}_{user_id}",
                        "flow_id": flow_id,
                        "flow_cta": flow_cta[:20],
                        "flow_action": "navigate",
                        "flow_action_payload": {
                            "screen": "FORM_SCREEN"
                        }
                    }
                }
            }
            success, res = await send_whatsapp_message(phone=phone, msg_type="interactive", interactive_obj=interactive_obj, credentials=credentials)
            if success:
                wamid = res.get('messages', [{}])[0].get('id', '')
                await log_bot_reply(user_id, phone, f"[WAPP Flow sent: {flow_id}]", wamid)
            else:
                print(f"DEBUG CHATBOT ERROR: Failed to send wapp_form to {phone}: {res}")
        return True
        
    elif action == 'url_button':
        btn_label = node_data.get('btn_label', 'Click Here')
        url = node_data.get('url', '')
        if url:
            interactive_obj = {
                "type": "cta_url",
                "body": {"text": "Please click the link below to proceed:"},
                "action": {
                    "name": "cta_url",
                    "parameters": {
                        "display_text": str(btn_label)[:20],
                        "url": str(url)
                    }
                }
            }
            success, res = await send_whatsapp_message(phone=phone, msg_type="interactive", interactive_obj=interactive_obj, credentials=credentials)
            if success:
                wamid = res.get('messages', [{}])[0].get('id', '')
                await log_bot_reply(user_id, phone, f"[URL Button sent: {btn_label} -> {url}]", wamid)
            else:
                print(f"DEBUG CHATBOT ERROR: Failed to send url_button to {phone}: {res}")
        return False
        
    elif action == 'create_ticket':
        dept = node_data.get('department', 'General')
        print(f"DEBUG: TICKET CREATED FOR {phone} in {dept}")
        return False
        
    elif action == 'add_tag':
        tag = node_data.get('tag_name')
        print(f"DEBUG: TAG {tag} added to {phone}")
        return False
        
    return False
