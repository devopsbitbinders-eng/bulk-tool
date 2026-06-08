import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

for db_file in ['campaigns.db', 'messenger.db', 'whatsapp.db', 'database.db']:
    print(f"\n{'='*60}")
    print(f"Checking: {db_file}")
    print('='*60)
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        
        # Check tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        print(f"Tables: {tables}")
        
        if 'campaigns' in tables:
            cur.execute("SELECT id, name, timestamp, total_numbers, sent_success, status FROM campaigns WHERE date(timestamp) >= '2026-05-19' ORDER BY timestamp ASC")
            rows = cur.fetchall()
            print(f"Campaigns after May 19: {len(rows)}")
            for r in rows:
                print(f"  ID:{r[0]} | {str(r[2])[:10]} | {r[3]} records | {r[4]} sent | {r[1]}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
