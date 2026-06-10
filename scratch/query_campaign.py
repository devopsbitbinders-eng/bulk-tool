from dotenv import load_dotenv
load_dotenv()
import asyncio
import database

async def check():
    await database.db.connect()
    res = await database.db.fetch_all("SELECT id, name, template_name FROM campaigns WHERE message_template LIKE '%Yadi aap Lucknow%'")
    for r in res:
        print(f"ID: {r['id']}, Name: {r['name']}, Template: {r['template_name']}")

if __name__ == '__main__':
    asyncio.run(check())
