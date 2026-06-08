import asyncio
from databases import Database

async def test():
    url = 'mysql+aiomysql://u802557144_message:Messenger2026@auth-db1559.hstgr.io:3306/u802557144_messenger'
    db = Database(url)
    try:
        await db.connect()
        print('SUCCESS!')
        await db.disconnect()
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test())
