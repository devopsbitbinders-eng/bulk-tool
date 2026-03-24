import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from database import get_db, init_db
from utils import get_now_utc

async def run():
    print("Testing duplicate key insert...")
    await init_db()
    db = await get_db()
    
    query = """
        INSERT INTO templates (name, category, language, status, content, components, last_synced)
        VALUES (:name, :category, :language, :status, :content, :components, :last_synced)
        ON DUPLICATE KEY UPDATE
            status = VALUES(status),
            content = VALUES(content),
            components = VALUES(components),
            last_synced = :last_synced
    """
    try:
        await db.execute(query, {
            "name": "test_template_duplicate", "category": "MARKETING", "language": "en_US", 
            "status": "APPROVED", "content": "Hello", "components": json.dumps([]),
            "last_synced": get_now_utc()
        })
        print("Success!")
    except Exception as e:
        print("Error during execute:", str(e))
        import traceback
        traceback.print_exc()

asyncio.run(run())
