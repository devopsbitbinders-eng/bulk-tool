import requests
import json
import asyncio
import random
import re
from utils import normalize_phone

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

def create_whatsapp_template(name, category, language, body_text=None, components=None, credentials=None, subtype=None):
    """Creates a new template on Meta API. Supports rich components."""
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    waba_id = credentials.get('waba_id', WHATSAPP_BUSINESS_ACCOUNT_ID) if credentials else WHATSAPP_BUSINESS_ACCOUNT_ID
    
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # If complex components provided, use them directly
    if components:
        final_components = components
    else:
        # Backward compatibility / simple body
        final_components = [{"type": "BODY", "text": body_text}]
        
        if category == "AUTHENTICATION":
            final_components.append({
                "type": "BUTTONS",
                "buttons": [{"type": "OTP", "otp_type": "COPY_CODE", "text": "Copy Code"}]
            })
            final_components.append({
                "type": "FOOTER",
                "text": "For your security, do not share this code."
            })

    payload = {
        "name": name,
        "category": category,
        "language": language,
        "components": final_components
    }
    if subtype and subtype != "DEFAULT":
        payload["category_subtype"] = subtype

    # DEBUG: Log the exact payload being sent to Meta
    print(f"DEBUG: Meta Template Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code in [200, 201], response.text
    except Exception as e:
        return False, str(e)

def create_whatsapp_otp_template(name, language, add_security_recommendation=False, code_expiration_minutes=None, credentials=None):
    """Creates a specialized AUTHENTICATION template on Meta API for OTPs."""
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    waba_id = credentials.get('waba_id', WHATSAPP_BUSINESS_ACCOUNT_ID) if credentials else WHATSAPP_BUSINESS_ACCOUNT_ID
    
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Meta AUTHENTICATION templates have strict component structures
    components = [
        {
            "type": "BODY",
            "add_security_recommendation": add_security_recommendation
        }
    ]

    # Expiration is defined at the FOOTER level in newer Meta API versions format
    if code_expiration_minutes and int(code_expiration_minutes) > 0:
        components.append({
            "type": "FOOTER",
            "code_expiration_minutes": int(code_expiration_minutes)
        })

    # Add the standard Copy Code button
    components.append({
        "type": "BUTTONS",
        "buttons": [
            {
                "type": "OTP",
                "otp_type": "COPY_CODE",
                "text": "Copy code"
            }
        ]
    })

    payload = {
        "name": name,
        "category": "AUTHENTICATION",
        "language": language,
        "components": components
    }

    print(f"DEBUG: Meta OTP Template Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code in [200, 201], response.text
    except Exception as e:
        return False, str(e)

def update_whatsapp_template(name, category, body_text=None, components=None, credentials=None):
    """Updates an existing template on Meta API.
    Note: Meta allows updating templates that are in certain states (e.g. APPROVED, REJECTED, etc. depending on what you change).
    For APPROVED templates, only certain fields can be updated without re-review.
    We use POST /{waba-id}/message_templates with the same name.
    """
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    waba_id = credentials.get('waba_id', WHATSAPP_BUSINESS_ACCOUNT_ID) if credentials else WHATSAPP_BUSINESS_ACCOUNT_ID
    
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # If complex components provided, use them directly
    if components:
        final_components = components
    else:
        final_components = [{"type": "BODY", "text": body_text}]

    payload = {
        "name": name,
        "category": category,
        "components": final_components
    }

    print(f"DEBUG: Meta Template Update Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        # Meta uses POST to the collection endpoint with the same name to update
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code in [200, 201], response.text
    except Exception as e:
        return False, str(e)

async def delete_whatsapp_template(name, credentials=None):
    """Deletes a template from Meta API."""
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    waba_id = credentials.get('waba_id', WHATSAPP_BUSINESS_ACCOUNT_ID) if credentials else WHATSAPP_BUSINESS_ACCOUNT_ID
    
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates"
    params = {"name": name}
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.delete(url, headers=headers, params=params)
        return response.status_code in [200, 204], response.text
    except Exception as e:
        return False, str(e)

async def upload_whatsapp_media(file_bytes, filename, mime_type, credentials):
    import requests
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    phone_id = credentials.get('phone_id', WHATSAPP_PHONE_NUMBER_ID) if credentials else WHATSAPP_PHONE_NUMBER_ID
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{phone_id}/media"
    headers = {"Authorization": f"Bearer {token}"}
    files = {
        'file': (filename, file_bytes, mime_type),
    }
    data = {'messaging_product': 'whatsapp'}
    try:
        response = requests.post(url, headers=headers, data=data, files=files)
        if response.status_code == 200:
            return response.json().get('id')
        print(f"DEBUG ERROR: Media Upload Failed {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"DEBUG: Error in upload_whatsapp_media: {str(e)}")
        return None

async def send_whatsapp_message(phone, message, msg_type="text", template_name=None, language_code="en_US", media_url=None, template_params=None, credentials=None, media_id=None):
    """Sends a message via Meta API. Supports templates with media and variables."""
    final_phone = normalize_phone(phone)

    if not USE_REAL_API:
        print(f"[MOCK API] Sending {msg_type} to {final_phone}: {message}")
        if msg_type == "template":
            print(f"       Template: {template_name} ({language_code})")
        await asyncio.sleep(random.randint(1, 2))
        return True, {"messages": [{"id": f"wamid.{random.randint(1000,9999)}"}]}

    # Real API Logic
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    phone_id = credentials.get('phone_id', WHATSAPP_PHONE_NUMBER_ID) if credentials else WHATSAPP_PHONE_NUMBER_ID
    
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    if msg_type == "template":
        # 1. Extract component definitions if available from credentials/context
        # (Assuming we might need to know which variables go where)
        # For now, we'll implement a smarter distribution logic
        
        const_components = []
        
        # 1. Header (Media or Text with Variables)
        if media_url:
            fmt = "image"
            if str(media_url).lower().endswith((".mp4", ".mov")): fmt = "video"
            elif str(media_url).lower().endswith((".pdf", ".doc", ".docx")): fmt = "document"
            
            const_components.append({
                "type": "header",
                "parameters": [{"type": fmt, fmt: {"link": media_url}}]
            })
        
        # 2. Body Variables (Default fallback: put all params in body if not specified otherwise)
        # In a more advanced version, we would check the template definition to see 
        # which indices {{n}} belong to which component.
        # For now, we'll try to be smart: if template_params is provided, we send them to BODY.
        if template_params:
            const_components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": str(v)} for v in template_params]
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": final_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": const_components
            }
        }
        # Debug Payload
        print(f"DEBUG: Meta Send Template Payload: {json.dumps(payload, indent=2)}")
    elif msg_type in ["image", "video", "document", "audio"]:
        payload = {
            "messaging_product": "whatsapp",
            "to": final_phone,
            "type": msg_type,
            msg_type: {"id": media_id}
        }
        if message:
            payload[msg_type]["caption"] = message
    else:
        # plain text
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
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        print(f"DEBUG: Error in send_whatsapp_message: {str(e)}")
        return False, str(e)

async def fetch_meta_templates(credentials):
    """Fetch all message templates from Meta WABA."""
    token = credentials.get('token')
    waba_id = credentials.get('waba_id')
    
    if not token or not waba_id:
        print("DEBUG: Missing credentials for template fetch")
        return []

    # Use the same version as configured
    version = credentials.get('version', WHATSAPP_VERSION)
    all_templates = []
    url = f"https://graph.facebook.com/{version}/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: Meta API Response Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                templates = data.get("data", [])
                
                for t in templates:
                    # Find all components for content preview to detect variables
                    full_content = []
                    body_text = ""
                    for comp in t.get("components", []):
                        ctype = comp.get("type")
                        ctext = comp.get("text", "")
                        if ctext:
                            full_content.append(ctext)
                        if ctype == "BODY":
                            body_text = ctext
                    
                    all_templates.append({
                        "name": t.get("name"),
                        "category": t.get("category"),
                        "language": t.get("language"),
                        "status": t.get("status"),
                        "content": body_text,
                        "full_content": "\n".join(full_content),
                        "components": json.dumps(t.get("components", []))
                    })
                
                # Handle pagination
                url = data.get("paging", {}).get("next")
            else:
                print(f"DEBUG: Meta Template Fetch Failed: {response.status_code} - {response.text}")
                break
        return all_templates
    except Exception as e:
        print(f"DEBUG: Error fetching templates: {str(e)}")
        return all_templates

def update_whatsapp_template(name, category, components, credentials=None):
    """Updates an existing template on Meta API by deleting and re-creating it."""
    token = credentials.get('token', WHATSAPP_TOKEN) if credentials else WHATSAPP_TOKEN
    waba_id = credentials.get('waba_id', WHATSAPP_BUSINESS_ACCOUNT_ID) if credentials else WHATSAPP_BUSINESS_ACCOUNT_ID

    # Meta does not support direct template updates via API for most fields.
    # The standard approach is to delete and recreate the template.
    # However, we can attempt a PATCH for category changes on some template versions.
    url = f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "category": category,
        "components": components
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in (200, 201):
            return True, None
        else:
            err = response.json().get("error", {}).get("message", response.text)
            return False, err
    except Exception as e:
        return False, str(e)
