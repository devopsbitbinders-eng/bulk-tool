import asyncio
from database import init_db

async def run():
    print("Testing init_db()...")
    await init_db()
    print("SUCCESS: init_db ran without syntax errors!")

asyncio.run(run())
