from dotenv import load_dotenv
load_dotenv()
import asyncio
import database
import json

async def check():
    await database.db.connect()
    rows = await database.db.fetch_all("""
        SELECT c.id, c.name, c.timestamp, c.template_name, c.media_url,
               COALESCE(c.message_template, (SELECT content FROM templates WHERE name = c.template_name LIMIT 1)) as message_template, 
               (SELECT components FROM templates WHERE name = c.template_name LIMIT 1) as template_components,
               (SELECT media_url FROM templates WHERE name = c.template_name LIMIT 1) as t_media_url
        FROM campaigns c 
        WHERE c.name LIKE 'Imp Member - Sheet43%'
        LIMIT 1
    """)
    if not rows: return
    
    r = dict(rows[0])
    c = {
        'id': r['id'],
        'name': r['name'],
        'timestamp': r['timestamp'].isoformat(),
        'template_name': r['template_name'],
        'media_url': r['media_url'],
        't_media_url': r['t_media_url'],
        'message_template': r['message_template'],
        'template_components': r['template_components']
    }
    
    # Simulate safe_json_response
    json_str = json.dumps(c, default=str)
    c_parsed = json.loads(json_str)
    
    js_code = f"""
    const c = {json.dumps(c_parsed)};
    let finalMediaHtml = '';
    let headerUrl = c.media_url || c.t_media_url || "";
    let headerType = "NONE";
    let buttonsHtml = '';
    let footerHtml = '';
    
    if (c.template_components) {{
        try {{
            const comps = JSON.parse(c.template_components);
            const header = comps.find(comp => comp.type === 'HEADER');
            if (header) {{
                headerType = header.format || "NONE";
                if (!headerUrl && header.example) {{
                    headerUrl = (header.example.header_handle && header.example.header_handle[0]) || 
                                (header.example.header_text && header.example.header_text[0]) || "";
                }}
            }}
            const footer = comps.find(comp => comp.type === 'FOOTER');
            if (footer && footer.text) {{
                footerHtml = `<div class="text-[10px] text-slate-400 mt-1">${{footer.text}}</div>`;
            }}
            const btns = comps.find(comp => comp.type === 'BUTTONS');
            if (btns && btns.buttons && btns.buttons.length > 0) {{
                buttonsHtml = '<div class="mt-2 border-t border-slate-200 pt-1 flex flex-col gap-1">BUTTONS INJECTED</div>';
            }}
        }} catch(e) {{
            console.error("PARSE ERROR", e);
        }}
    }}
    
    if (headerUrl && headerType !== "NONE" && headerType !== "TEXT") {{
        if (headerType === "VIDEO") {{
            finalMediaHtml = `<video src="${{headerUrl}}" controls></video>`;
        }}
    }}
    
    console.log("FINAL MEDIA:", finalMediaHtml);
    console.log("FOOTER:", footerHtml);
    console.log("BUTTONS:", buttonsHtml);
    """
    with open("scratch/test2.js", "w", encoding="utf-8") as f:
        f.write(js_code)

if __name__ == '__main__':
    asyncio.run(check())
