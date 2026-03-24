from databases import Database
import os
import asyncio

# Fallback to local SQLite for development
DEFAULT_DB_URL = "sqlite:///campaigns.db"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

# For Hostinger MySQL, the URL should be: mysql://user:pass@host:port/db
# We automatically prefix with mysql+aiomysql:// for the databases library
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://", 1)

if "charset" not in DATABASE_URL and "mysql" in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&charset=utf8mb4"
    else:
        DATABASE_URL += "?charset=utf8mb4"

db = Database(DATABASE_URL)

async def init_db():
    await db.connect()
    is_mysql = DATABASE_URL.startswith("mysql")
    
    # helper for auto-increment syntax
    auto_inc = "AUTO_INCREMENT" if is_mysql else "AUTOINCREMENT"
    text_type = "VARCHAR(255)" if is_mysql else "TEXT"
    
    # Charset for MySQL
    charset = "" # Deprecated for columns
    table_opts = "DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci" if is_mysql else ""

    # Create Chat Messages Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            phone TEXT,
            message TEXT,
            direction TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            wa_message_id TEXT,
            is_read BOOLEAN DEFAULT 0
        )
    """)

    # 1. Campaigns Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_numbers INTEGER,
            sent_success INTEGER DEFAULT 0,
            sent_failed INTEGER DEFAULT 0,
            status TEXT
        ) {table_opts}
    """)

    # 2. Messages Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            campaign_id INTEGER,
            phone TEXT,
            message TEXT,
            status TEXT,
            error_message TEXT,
            whatsapp_message_id TEXT,
            row_data TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # 3. Templates Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            name {text_type},
            category TEXT,
            language TEXT,
            status TEXT,
            content TEXT,
            components TEXT,
            variable_map TEXT,
            last_synced DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        ) {table_opts}
    """)

    # 4. User Credentials Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS user_credentials (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            whatsapp_token TEXT,
            phone_number_id TEXT,
            waba_id TEXT,
            phone_number TEXT,
            is_active INTEGER DEFAULT 1,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # 5. Users Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY {auto_inc},
            username {text_type} UNIQUE,
            password_hash TEXT,
            salt TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # Migrations for existing SQLite/MySQL
    if is_mysql:
        # For MySQL, ensure existing tables are converted
        tables = ["campaigns", "messages", "templates", "user_credentials"]
        for table in tables:
            try: await db.execute(f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            except: pass
    
    try: await db.execute("ALTER TABLE chat_messages ADD COLUMN user_id INTEGER")
    except: pass
    try: await db.execute("ALTER TABLE campaigns ADD COLUMN user_id INTEGER")
    except: pass
    try: await db.execute("ALTER TABLE messages ADD COLUMN user_id INTEGER")
    except: pass
    try: await db.execute("ALTER TABLE templates ADD COLUMN user_id INTEGER")
    except: pass
    try: await db.execute("ALTER TABLE user_credentials ADD COLUMN user_id INTEGER")
    except: pass
    
    try: await db.execute("ALTER TABLE messages ADD COLUMN whatsapp_message_id TEXT")
    except: pass
    try: await db.execute("ALTER TABLE templates ADD COLUMN components TEXT")
    except: pass
    try: await db.execute("ALTER TABLE templates ADD COLUMN variable_map TEXT")
    except: pass

    pass # Keep connection pool alive for the actual request

async def get_db():
    # In databases, we use the global db object. 
    # This function is kept for backward compatibility if needed.
    if not db.is_connected:
        await db.connect()
    return db
