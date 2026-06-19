import asyncio
from databases import Database
import os
from dotenv import load_dotenv

load_dotenv()

async def run():
    db_url = os.environ.get("DATABASE_URL")
    if db_url.startswith("mysql://"):
        db_url = db_url.replace("mysql://", "mysql+aiomysql://", 1)
    db = Database(db_url)
    await db.connect()
    
    # Get the latest campaign file
    file_record = await db.fetch_one("SELECT id, campaign_id, LENGTH(csv_content) as size, csv_content FROM campaign_files ORDER BY id DESC LIMIT 1")
    if file_record:
        print(f"File ID: {file_record['id']} - Size: {file_record['size']} bytes")
        # Save it
        with open("last_uploaded.csv", "wb") as f:
            if isinstance(file_record['csv_content'], str):
                f.write(file_record['csv_content'].encode('utf-8'))
            else:
                f.write(file_record['csv_content'])
        print("Saved to last_uploaded.csv")
    else:
        print("No campaign files found.")
            
    await db.disconnect()

asyncio.run(run())
