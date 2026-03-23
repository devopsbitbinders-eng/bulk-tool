import asyncio
import os
import sys
from fastapi.templating import Jinja2Templates

# Add current dir to path
sys.path.append('c:/Users/kajal/Downloads/messanger')

from main import get_dashboard_stats

async def main():
    try:
        print("Starting render test...")
        BASE_DIR = 'c:/Users/kajal/Downloads/messanger'
        templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
        stats = await get_dashboard_stats()
        
        # Mocking objects that might be expected
        class MockRequest:
            pass

        print("Attempting to render index.html...")
        # Note: we use .get_template().render() for standalone test
        # but in FastAPI it's TemplateResponse.
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))
        template = env.get_template("index.html")
        
        html = template.render({
            "request": MockRequest(),
            "campaigns": [],
            "templates": [],
            "templates_json": "[]",
            "fb_app_id": "test",
            "fb_config_id": "test",
            "linked_phone": "test",
            "stats": stats
        })
        print("Render SUCCESS (first 100 chars):", html[:100].replace('\n', ' '))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
