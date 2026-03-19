import sqlite3
import os

DB_PATH = "campaigns.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print("Database does not exist. No migration needed.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if row_data already exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'row_data' not in columns:
            print("Adding 'row_data' column to 'messages' table...")
            cursor.execute("ALTER TABLE messages ADD COLUMN row_data TEXT")
            conn.commit()
            print("Migration successful.")
        else:
            print("'row_data' column already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
