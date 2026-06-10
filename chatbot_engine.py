import json
from datetime import datetime, timedelta, timezone
from database import get_db
from whatsapp_service import send_whatsapp_message, get_active_credentials
import asyncio

async def process_chatbot_message(user_id: int, phone: str, body: str, msg_type: str):
    """
    State machine logic for processing incoming WhatsApp messages.
    """
    db = await get_db()
    
    # Extract raw text if it's text, otherwise it's media or button response
    # We will handle interactive buttons (list replies, button replies) later
    # For now, if it's text, we check for triggers.
    text_input = ""
    interactive_id = None
    
    # Meta Interactive message payload parsing
    if msg_type == "text":
        text_input = str(body).strip().lower()
    elif msg_type == "interactive":
        try:
            # interactive payload was saved as JSON in `body` or just passed directly.
            # Usually, interactive is not handled by the current webhook correctly (it stores as "[Received interactive]").
            # Let's assume for now we use text.
            pass
        except: pass

    # 1. Check for Active Session
    session = await db.fetch_one("""
        SELECT * FROM user_sessions 
        WHERE user_id = :uid AND phone_number = :phone 
        LIMIT 1
    """, {"uid": user_id, "phone": phone})
    
    now_utc = datetime.now(timezone.utc)
    
    if session:
        # Check 24-hour rule
        last_interaction = session['last_interaction_at']
        # Convert naive to aware if needed (assuming DB returns naive UTC)
        if last_interaction.tzinfo is None:
            last_interaction = last_interaction.replace(tzinfo=timezone.utc)
            
        if (now_utc - last_interaction).total_seconds() > 24 * 3600:
            print(f"DEBUG CHATBOT: Session for {phone} expired (24h rule).")
            # We could delete the session or reset it.
            await db.execute("DELETE FROM user_sessions WHERE id = :id", {"id": session['id']})
            session = None

    if session:
        # We have an active session, let's process the state
        flow_id = session['flow_id']
        current_node_id = session['current_node_id']
        
        flow = await db.fetch_one("SELECT flow_json FROM flows WHERE id = :fid", {"fid": flow_id})
        if not flow:
            return # Flow deleted
            
        try:
            flow_data = json.loads(flow['flow_json'])
        except:
            return
            
        nodes = flow_data.get('nodes', [])
        edges = flow_data.get('edges', [])
        
        # Determine the next node based on edges from current_node_id
        # Simple transition logic: if edge label matches text_input
        # OR if there is a default/fallback edge.
        # For Milestone 2/3, let's build a simple logic:
        # Find edges originating from current_node_id
        possible_edges = [e for e in edges if e.get('source') == current_node_id]
        
        next_node_id = None
        fallback_node_id = None
        
        for edge in possible_edges:
            edge_label = str(edge.get('label', '')).lower().strip()
            if edge_label == text_input:
                next_node_id = edge.get('target')
                break
            if edge_label == '*' or edge_label == 'fallback':
                fallback_node_id = edge.get('target')
        
        if not next_node_id and fallback_node_id:
            next_node_id = fallback_node_id
            
        if next_node_id:
            await execute_node(user_id, phone, next_node_id, nodes)
            # Update session
            await db.execute("""
                UPDATE user_sessions 
                SET current_node_id = :node, last_interaction_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """, {"node": next_node_id, "id": session['id']})
        else:
            print(f"DEBUG CHATBOT: No transition found from {current_node_id} for input {text_input}")
            
    else:
        # No active session, check for Triggers
        if text_input:
            trigger = await db.fetch_one("""
                SELECT flow_id FROM triggers 
                WHERE user_id = :uid AND LOWER(keyword) = :kw 
                LIMIT 1
            """, {"uid": user_id, "kw": text_input})
            
            if trigger:
                flow_id = trigger['flow_id']
                flow = await db.fetch_one("SELECT flow_json FROM flows WHERE id = :fid", {"fid": flow_id})
                if flow:
                    try:
                        flow_data = json.loads(flow['flow_json'])
                        nodes = flow_data.get('nodes', [])
                        
                        # Find the start node (usually type='start' or the first node)
                        start_node = next((n for n in nodes if n.get('type') == 'start'), None)
                        if not start_node and nodes:
                            start_node = nodes[0] # fallback
                            
                        if start_node:
                            # Create session
                            await db.execute("""
                                INSERT INTO user_sessions (user_id, phone_number, flow_id, current_node_id, state_data)
                                VALUES (:uid, :phone, :fid, :node, '{}')
                            """, {
                                "uid": user_id, "phone": phone, "fid": flow_id, "node": start_node['id']
                            })
                            # Execute the start node (which might just transition to the next or send a message)
                            await execute_node(user_id, phone, start_node['id'], nodes)
                    except Exception as e:
                        print(f"DEBUG CHATBOT ERROR: {e}")

async def execute_node(user_id: int, phone: str, node_id: str, nodes: list):
    node = next((n for n in nodes if n.get('id') == node_id), None)
    if not node: return
    
    node_data = node.get('data', {})
    action = node_data.get('action') # 'send_message', 'send_template', etc.
    
    if action == 'send_message':
        message_text = node_data.get('text', '')
        if message_text:
            credentials = await get_active_credentials(user_id)
            # Async run to not block processing
            asyncio.create_task(send_whatsapp_message(
                phone=phone,
                message=message_text,
                msg_type="text",
                credentials=credentials
            ))
