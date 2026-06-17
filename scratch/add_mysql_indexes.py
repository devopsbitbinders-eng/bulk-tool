import asyncio
from dotenv import load_dotenv
load_dotenv()
import database

async def apply_mysql_indexes():
    await database.db.connect()
    
    indexes = [
        "CREATE INDEX idx_msg_usr_st_ts ON messages (user_id, status(20), timestamp)",
        "CREATE INDEX idx_chat_usr_dir_ts ON chat_messages (user_id, direction(20), timestamp)"
    ]
    
    for idx_sql in indexes:
        try:
            print(f"Executing: {idx_sql}")
            await database.db.execute(idx_sql)
            print("Success")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(apply_mysql_indexes())
