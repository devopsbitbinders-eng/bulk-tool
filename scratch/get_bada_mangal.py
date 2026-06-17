import asyncio
import database
from dotenv import load_dotenv

load_dotenv()

async def get_template():
    await database.db.connect()
    res = await database.db.fetch_all("SELECT content FROM templates")
    for r in res:
        if r['content'] and 'Bada Mangal' in r['content']:
            print(repr(r['content']))

if __name__ == '__main__':
    asyncio.run(get_template())
