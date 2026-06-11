import httpx
import json

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
        if q_type in ['TEXT', 'NUMBER', 'DATE', 'IMAGE']:
            input_type = "text"
            if q_type == 'NUMBER': input_type = "number"
            if q_type == 'DATE': input_type = "date"
            children.append({
                "type": "TextInput",
                "name": f"q_{idx}",
                "label": str(q_text)[:30],
                "input-type": input_type,
                "required": True
            })
        elif q_type == 'LIST':
            children.append({
                "type": "Dropdown",
                "name": f"q_{idx}",
                "label": str(q_text)[:30],
                "options": [
                    {"id": "opt1", "title": "Option 1"},
                    {"id": "opt2", "title": "Option 2"}
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
      "version": "3.1",
      "routing_model": {
        "START": "SCREEN_1"
      },
      "screens": [
        {
          "id": "SCREEN_1",
          "title": str(flow_name)[:20],
          "terminal": True,
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
    
    import re
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', flow_name.replace(" ", "_"))[:20].lower()
    
    # 1. Create Flow
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://graph.facebook.com/v18.0/{waba_id}/flows",
            headers=headers,
            data={
                "name": safe_name,
                "categories": "[\"LEAD_GENERATION\"]"
            }
        )
        if res.status_code != 200:
            raise Exception(f"Failed to create flow: {res.text}")
            
        flow_id = res.json().get('id')
        
        # 2. Upload Asset
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp:
            json.dump(flow_json, temp)
            temp_path = temp.name
            
        try:
            with open(temp_path, 'rb') as f:
                res2 = await client.post(
                    f"https://graph.facebook.com/v18.0/{flow_id}/assets",
                    headers=headers,
                    data={"name": "flow.json", "asset_type": "FLOW_JSON"},
                    files={"file": ("flow.json", f, "application/json")}
                )
        finally:
            os.remove(temp_path)
            
        if res2.status_code != 200:
            raise Exception(f"Failed to upload flow asset: {res2.text}")
            
        # 3. Publish Flow
        res3 = await client.post(
            f"https://graph.facebook.com/v18.0/{flow_id}/publish",
            headers=headers
        )
        if res3.status_code != 200:
            raise Exception(f"Failed to publish flow: {res3.text}")
            
        return str(flow_id)
