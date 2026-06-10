from dotenv import load_dotenv
load_dotenv()
import asyncio
import database

async def check():
    await database.db.connect()
    res = await database.db.fetch_all("SELECT id, name, template_name FROM campaigns ORDER BY timestamp DESC LIMIT 5")
    for r in res:
        print(dict(r))

if __name__ == '__main__':
    asyncio.run(check())
