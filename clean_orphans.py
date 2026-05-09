import sqlite3
import os

db_path = "database.db"

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found in current directory!")
    # Let's try to find it
    for file in os.listdir('.'):
        if file.endswith('.db'):
            db_path = file
            print(f"Found database file: {db_path}")
            break
    else:
        print("Could not find any .db file in the current directory.")
        exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Checking for orphan messages...")
    
    # Find messages with campaign_id that does not exist in campaigns
    cursor.execute("""
        SELECT id, campaign_id FROM messages 
        WHERE campaign_id IS NOT NULL AND campaign_id != '' AND campaign_id NOT IN (SELECT id FROM campaigns)
    """)
    orphans = cursor.fetchall()
    print(f"Found {len(orphans)} orphan messages.")
    
    if orphans:
        print("Deleting orphan messages...")
        cursor.execute("""
            DELETE FROM messages 
            WHERE campaign_id IS NOT NULL AND campaign_id != '' AND campaign_id NOT IN (SELECT id FROM campaigns)
        """)
        conn.commit()
        print("Successfully deleted orphan messages!")
    else:
        print("No orphan messages found. Your database is clean or campaigns are intact.")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
