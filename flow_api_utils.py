import httpx
import json
import re
import tempfile
import os

async def create_and_publish_meta_flow(waba_id: str, access_token: str, flow_name: str, questions: list) -> str:
    """
    Translates UI form questions to Meta Flow JSON, creates the flow, uploads assets, and publishes.
    Returns the meta_flow_id. Raises Exception on error.
    """
    children = []
    children.append({
        "type": "TextHeading",
        "text": "Please provide the details below"
    })
    
    for idx, q in enumerate(questions):
        q_type = q.get('format')
        q_text = q.get('text')
        
        # TEXT, NUMBER, and IMAGE components mapping
        if q_type in ['TEXT', 'NUMBER', 'IMAGE']:
            input_type = "text"
            if q_type == 'NUMBER': 
                input_type = "number"
            children.append({
                "type": "TextInput",
                "name": f"q_{idx}",
                "label": str(q_text)[:30],
                "input-type": input_type,
                "required": True
            })
            
        # Official DatePicker component for version 7.3
        elif q_type == 'DATE':
            children.append({
                "type": "DatePicker",
                "name": f"q_{idx}",
                "label": str(q_text)[:30],
                "required": True
            })
            
        elif q_type == 'LIST':
            children.append({
                "type": "Dropdown",
                "name": f"q_{idx}",
                "label": str(q_text)[:30],
                "options": [
                    {"id": "opt_a", "title": "Option 1"},
                    {"id": "opt_b", "title": "Option 2"}
                ],
                "required": True
            })
            
    payload = {"form_submitted": "true"}
    for idx, q in enumerate(questions):
        payload[f"q_{idx}"] = f"${{form.q_{idx}}}"
        
    children.append({
        "type": "Footer",
        "label": "Submit",
        "on-click-action": {
            "name": "complete",
            "payload": payload
        }
    })
    
    flow_json = {
      "version": "7.3",
      "screens": [
        {
          "id": "FORM_SCREEN",
          "title": str(flow_name)[:20],
          "terminal": True,
          "success": True,
          "data": {},
          "layout": {
            "type": "SingleColumnLayout",
            "children": children
          }
        }
      ]
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', flow_name.replace(" ", "_"))[:20].lower()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create Flow (v21.0)
        res = await client.post(
            f"https://graph.facebook.com/v21.0/{waba_id}/flows",
            headers=headers,
            data={
                "name": safe_name,
                "categories": "[\"LEAD_GENERATION\"]"
            }
        )
        if res.status_code != 200:
            raise Exception(f"Failed to create flow: {res.text}")
            
        flow_id = res.json().get('id')
        
        # 2. Upload Asset (v21.0)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp:
            json.dump(flow_json, temp)
            temp_path = temp.name
            
        try:
            with open(temp_path, 'rb') as f:
                res2 = await client.post(
                    f"https://graph.facebook.com/v21.0/{flow_id}/assets",
                    headers=headers,
                    data={"name": "flow.json", "asset_type": "FLOW_JSON"},
                    files={"file": ("flow.json", f, "application/json")}
                )
        finally:
            os.remove(temp_path)
            
        if res2.status_code != 200:
            raise Exception(f"Failed to upload flow asset: {res2.text}")
            
        # 3. Publish Flow (v21.0)
        res3 = await client.post(
            f"https://graph.facebook.com/v21.0/{flow_id}/publish",
            headers=headers
        )
        if res3.status_code != 200:
            url_err = f"https://graph.facebook.com/v21.0/{flow_id}?fields=validation_errors"
            res_err = await client.get(url_err, headers=headers)
            raise Exception(f"Failed to publish flow: {res3.text}. Validation Errors: {res_err.text}")
            
        return str(flow_id)