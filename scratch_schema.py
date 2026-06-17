import asyncio
from database import db

async def main():
    await db.connect()
    rows = await db.fetch_all('SHOW CREATE TABLE messages')
    print(rows[0][1])
    await db.disconnect()

asyncio.run(main())
