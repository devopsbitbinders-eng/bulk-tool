from dotenv import load_dotenv
load_dotenv()
import asyncio
import database
import json

async def check():
    await database.db.connect()
    res = await database.db.fetch_one("SELECT components FROM templates WHERE name='monthyl_expense'")
    comps_str = res['components']
    
    js_code = f"""
    const c = {{ template_components: {json.dumps(comps_str)} }};
    let buttonsHtml = '';
    let footerHtml = '';
    if (c.template_components) {{
        try {{
            const comps = JSON.parse(c.template_components);
            const footer = comps.find(comp => comp.type === 'FOOTER');
            if (footer && footer.text) {{
                footerHtml = `<div class="text-[10px] text-slate-400 mt-1">${{footer.text}}</div>`;
            }}
            const btns = comps.find(comp => comp.type === 'BUTTONS');
            if (btns && btns.buttons && btns.buttons.length > 0) {{
                buttonsHtml = 'BUTTONS FOUND';
            }}
            console.log("FOOTER:", footerHtml);
            console.log("BUTTONS:", buttonsHtml);
        }} catch(e) {{
            console.error(e);
        }}
    }}
    """
    with open("scratch/test.js", "w", encoding="utf-8") as f:
        f.write(js_code)

if __name__ == '__main__':
    asyncio.run(check())
