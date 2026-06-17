from dotenv import load_dotenv
load_dotenv()
import asyncio
import database

async def check():
    await database.db.connect()
    r = await database.db.fetch_one("SELECT components FROM templates WHERE name='monthyl_expense'")
    if r:
        print(repr(r['components'][:150]))
        print("Contains actual newline:", "\n" in r['components'])
        print("Contains backslash n:", "\\n" in r['components'])

if __name__ == '__main__':
    asyncio.run(check())
