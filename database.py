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
            status TEXT DEFAULT 'sent',
            error_message TEXT,
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
            status TEXT,
            message_template TEXT,
            msg_type TEXT,
            template_name TEXT,
            language_code TEXT,
            mappings TEXT,
            phone_col TEXT,
            scheduled_at DATETIME,
            media_url TEXT,
            meta_media_id TEXT,
            retry_enabled BOOLEAN DEFAULT 0,
            retry_max_count INTEGER DEFAULT 0,
            retry_interval_hours INTEGER DEFAULT 0
        ) {table_opts}
    """)
    
    # 1.1 Migration for media_url
    try:
        await db.execute("ALTER TABLE campaigns ADD COLUMN media_url TEXT")
        print("MIGRATION: Added media_url to campaigns")
    except Exception as e:
        if "Duplicate column" not in str(e) and "already exists" not in str(e):
            print(f"MIGRATION ERROR (media_url): {e}")
    try:
        await db.execute("ALTER TABLE campaigns ADD COLUMN meta_media_id TEXT")
        print("MIGRATION: Added meta_media_id to campaigns")
    except Exception as e:
        if "Duplicate column" not in str(e) and "already exists" not in str(e):
            print(f"MIGRATION ERROR (meta_media_id): {e}")

    # 1.2 Migration for retry settings
    try: await db.execute("ALTER TABLE campaigns ADD COLUMN retry_enabled BOOLEAN DEFAULT 0")
    except: pass
    try: await db.execute("ALTER TABLE campaigns ADD COLUMN retry_max_count INTEGER DEFAULT 0")
    except: pass
    try: await db.execute("ALTER TABLE campaigns ADD COLUMN retry_interval_hours INTEGER DEFAULT 0")
    except: pass

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
            media_url TEXT,
            last_synced DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name, language)
        ) {table_opts}
    """)

    # Migration: media_url in templates
    try: await db.execute("ALTER TABLE templates ADD COLUMN media_url TEXT")
    except: pass

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
            business_name {text_type},
            password_hash TEXT,
            salt TEXT,
            is_approved BOOLEAN DEFAULT 0,
            is_admin BOOLEAN DEFAULT 0,
            expiry_date DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # 6. Access Requests Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS access_requests (
            id INTEGER PRIMARY KEY {auto_inc},
            name TEXT,
            contact TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # 7. Invite Keys Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS invite_keys (
            id INTEGER PRIMARY KEY {auto_inc},
            key_code {text_type} UNIQUE,
            is_used BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # 8. Campaign Files Table
    long_text_type = "LONGTEXT" if is_mysql else "TEXT"
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS campaign_files (
            id INTEGER PRIMARY KEY {auto_inc},
            campaign_id INTEGER,
            csv_content {long_text_type},
            processed_rows INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending'
        ) {table_opts}
    """)

    # 9. Chatbot Flows Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS flows (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            name {text_type},
            flow_json {long_text_type},
            status TEXT DEFAULT 'draft',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # 10. Chatbot Triggers Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS wapp_forms (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            name {text_type},
            meta_flow_id {text_type},
            questions_json {long_text_type},
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS triggers (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            keyword {text_type},
            flow_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # 11. User Sessions Table (Database Fallback / Primary if Redis is not used)
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            phone_number {text_type},
            flow_id INTEGER,
            current_node_id {text_type},
            state_data {long_text_type},
            last_interaction_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, phone_number)
        ) {table_opts}
    """)

    # Migrations for existing SQLite/MySQL
    if is_mysql:
        # For MySQL, ensure existing tables are converted
        tables = ["campaigns", "messages", "templates", "user_credentials", "users", "access_requests", "invite_keys"]
        for table in tables:
            try: await db.execute(f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            except: pass
    
    # Migration: Ensure columns exist in the 'users' table
    try: await db.execute("ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT 0")
    except: pass
    try: await db.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    except: pass
    try: await db.execute(f"ALTER TABLE users ADD COLUMN business_name {text_type}")
    except: pass
    try: await db.execute("ALTER TABLE users ADD COLUMN expiry_date DATETIME")
    except: pass

    # Other migrations
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
    
    # Migration: tag in messages
    try: await db.execute("ALTER TABLE messages ADD COLUMN tag TEXT")
    except: pass
    
    # Migration: chat_messages status and error_message
    try: await db.execute("ALTER TABLE chat_messages ADD COLUMN status TEXT DEFAULT 'sent'")
    except: pass
    try: await db.execute("ALTER TABLE chat_messages ADD COLUMN error_message TEXT")
    except: pass
    
    # Indexes for performance
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_wa_id ON messages (whatsapp_message_id(50))")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_wa_id ON chat_messages (wa_message_id(50))")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_phone_user ON messages (phone(20), user_id)")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_phone_user ON chat_messages (phone(20), user_id)")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_campaign ON messages (campaign_id)")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_campaign_status ON messages (campaign_id, status)")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_msg_usr_ts ON messages (user_id, timestamp)")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_msg_usr_st_ts ON messages (user_id, status(20), timestamp)")
    except: pass
    try: await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_usr_dir_ts ON chat_messages (user_id, direction(20), timestamp)")
    except: pass

    # Ultimate Database-Level Duplicate Prevention
    try: 
        if is_mysql:
            await db.execute("CREATE UNIQUE INDEX idx_uniq_campaign_phone ON messages (campaign_id, phone(50))")
        else:
            await db.execute("CREATE UNIQUE INDEX idx_uniq_campaign_phone ON messages (campaign_id, phone)")
    except Exception as e:
        if "Duplicate key name" not in str(e):
            print(f"MIGRATION ERROR (unique_idx): {e}")

    # Webhook Logs for debugging
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS webhook_logs (
            id INTEGER PRIMARY KEY {auto_inc},
            payload TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # Opt Outs Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS opt_outs (
            id INTEGER PRIMARY KEY {auto_inc},
            phone {text_type} UNIQUE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    # Agents Table
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id INTEGER,
            name {text_type},
            email {text_type},
            mobile {text_type},
            password_hash TEXT,
            role {text_type},
            profile_image_url TEXT,
            status TEXT DEFAULT 'active',
            online_status TEXT DEFAULT 'offline',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) {table_opts}
    """)

    pass # Keep connection pool alive for the actual request

async def get_db():
    # In databases, we use the global db object. 
    # This function is kept for backward compatibility if needed.
    if not db.is_connected:
        await db.connect()
    # Check for scheduled_at
    try:
        await db.execute("SELECT scheduled_at FROM campaigns LIMIT 1")
    except:
        print("MIGRATION: Adding scheduled_at to campaigns table")
        try:
            await db.execute("ALTER TABLE campaigns ADD COLUMN scheduled_at DATETIME")
        except Exception as e:
            print(f"MIGRATION ERROR (scheduled_at): {e}")

    return db
