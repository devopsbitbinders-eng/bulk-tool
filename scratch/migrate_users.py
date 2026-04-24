import sqlite3
import os

db_path = 'campaigns.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        # Add columns if they don't exist
        try:
            conn.execute('ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT 1')
            print("Added is_approved column")
        except:
            print("is_approved column already exists")
            conn.execute('UPDATE users SET is_approved = 1')

        try:
            conn.execute('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0')
            print("Added is_admin column")
        except:
            print("is_admin column already exists")
        
        # Set the first user as admin
        cursor = conn.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1")
        first_user = cursor.fetchone()
        if first_user:
            conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (first_user[0],))
            print(f"User ID {first_user[0]} is now an Admin")

        conn.commit()
        print("Migration and approval complete!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print("Database not found")
