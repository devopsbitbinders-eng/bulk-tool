import sqlite3
import os
import json

db_path = "database.db"

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found!")
    for file in os.listdir('.'):
        if file.endswith('.db'):
            db_path = file
            print(f"Found database file: {db_path}")
            break
    else:
        print("Could not find any .db file.")
        exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Running chat contacts query...")
    
    # Find a user to test with
    cursor.execute("SELECT id, username FROM users LIMIT 1")
    user = cursor.fetchone()
    if not user:
        print("No users found in database!")
        exit(1)
        
    u_id = user[0]
    print(f"Testing with user_id: {u_id} ({user[1]})")
    
    query = """
        SELECT t.phone, 
               MAX(CASE WHEN c.is_read = 0 AND c.direction = 'inbound' THEN 1 ELSE 0 END) as has_unread,
               (SELECT row_data FROM messages WHERE phone = t.phone AND user_id = ? AND row_data IS NOT NULL ORDER BY timestamp DESC LIMIT 1) as row_data
        FROM (
            SELECT phone FROM messages WHERE user_id = ? AND status IN ('sent', 'delivered', 'read')
            UNION
            SELECT phone FROM chat_messages WHERE user_id = ?
        ) t
        LEFT JOIN chat_messages c ON t.phone = c.phone AND c.user_id = ?
        WHERE t.phone IS NOT NULL AND t.phone != ''
        GROUP BY t.phone
        ORDER BY MAX(c.timestamp) DESC, t.phone ASC
    """
    
    cursor.execute(query, (u_id, u_id, u_id, u_id))
    rows = cursor.fetchall()
    print(f"Successfully returned {len(rows)} contacts.")
    
    for r in rows[:5]:
        print(f"Phone: {r[0]}, Unread: {r[1]}, Data: {r[2][:50] if r[2] else 'None'}...")
        
except Exception as e:
    import traceback
    print(f"\n❌ ERROR RUNNING QUERY: {e}")
    traceback.print_exc()
finally:
    conn.close()
