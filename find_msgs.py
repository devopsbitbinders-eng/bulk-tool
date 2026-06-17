import asyncio
import json
import sys
import os
sys.path.append(os.getcwd())
from database import get_db

async def main():
    db = await get_db()
    logs = await db.fetch_all("SELECT payload FROM webhook_logs ORDER BY id DESC")
    for log in logs:
        try:
            data = json.loads(log['payload'])
            entries = data.get('entry', [])
            for entry in entries:
                for change in entry.get('changes', []):
                    messages = change.get('value', {}).get('messages', [])
                    for msg in messages:
                        print("FOUND MESSAGE:", json.dumps(msg))
        except Exception as e:
            pass

asyncio.run(main())
