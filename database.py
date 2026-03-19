import aiosqlite
import os

DB_PATH = "campaigns.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_numbers INTEGER,
                sent_success INTEGER DEFAULT 0,
                sent_failed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Pending'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                phone TEXT,
                message TEXT,
                status TEXT,
                error_message TEXT,
                row_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                category TEXT,
                language TEXT,
                status TEXT DEFAULT 'PENDING',
                content TEXT,
                last_synced DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                whatsapp_token TEXT,
                phone_number_id TEXT,
                waba_id TEXT,
                phone_number TEXT,
                is_active INTEGER DEFAULT 1,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db
