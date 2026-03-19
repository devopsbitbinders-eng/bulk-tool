import requests
import json
import asyncio
import random
import re

# Configuration
USE_REAL_API = True  
WHATSAPP_TOKEN = "" # Now fetched dynamically from database after Facebook Login
WHATSAPP_PHONE_NUMBER_ID = ""
WHATSAPP_BUSINESS_ACCOUNT_ID = ""
WHATSAPP_VERSION = "v21.0"

def get_whatsapp_templates(credentials=None):
    """Fetches templates from Meta API."""
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    waba_id = credentials.get('waba_id', WHATSAPP_BUSINESS_ACCOUNT_ID) if credentials else WHATSAPP_BUSINESS_ACCOUNT_ID
    
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            print(f"DEBUG ERROR Meta API {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"DEBUG: Error fetching templates: {str(e)}")
        return []

def create_whatsapp_template(name, category, language, body_text, credentials=None):
    """Creates a new template on Meta API."""
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    waba_id = credentials.get('waba_id', WHATSAPP_BUSINESS_ACCOUNT_ID) if credentials else WHATSAPP_BUSINESS_ACCOUNT_ID
    
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "category": category,
        "language": language,
        "components": [
            {
                "type": "BODY",
                "text": body_text
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code in [200, 201], response.text
    except Exception as e:
        return False, str(e)

async def send_whatsapp_message(phone, message, msg_type="text", template_name=None, language_code="en_US", credentials=None):
    # Normalize phone: Ensure it has a country code.
    clean_phone = re.sub(r'\D', '', str(phone))
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
    
    final_phone = clean_phone.replace('+', '')

    if not USE_REAL_API:
        print(f"[MOCK API] Sending {msg_type} to {final_phone}: {message}")
        if msg_type == "template":
            print(f"       Template: {template_name} ({language_code})")
        await asyncio.sleep(random.randint(1, 2))
        return True, None

    # Real API Logic
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    phone_id = credentials.get('phone_id', WHATSAPP_PHONE_NUMBER_ID) if credentials else WHATSAPP_PHONE_NUMBER_ID
    
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    if msg_type == "template":
        params = []
        if isinstance(message, list):
            params = [{"type": "text", "text": str(v)} for v in message]
        else:
            params = [{"type": "text", "text": str(message)}]

        payload = {
            "messaging_product": "whatsapp",
            "to": final_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": params
                    }
                ]
            }
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": final_phone,
            "type": "text",
            "text": {"body": message}
        }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code not in [200, 201]:
            print(f"DEBUG ERROR: Meta API {response.status_code} - {response.text}")
        
        if response.status_code == 200 or response.status_code == 201:
            return True, None
        else:
            return False, response.text
    except Exception as e:
        print(f"DEBUG: Error in send_whatsapp_message: {str(e)}")
        return False, str(e)
