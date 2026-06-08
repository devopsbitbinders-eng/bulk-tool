"""
Check karo ki old server (auth-db1559) abhi bhi accessible hai ya nahi
Aur agar hai toh wahan se campaign data nikalo
"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from databases import Database

OLD_URL = "mysql+aiomysql://u802557144_message:Messenger2026@auth-db1559.hstgr.io:3306/u802557144_messenger?charset=utf8mb4"
NEW_URL = "mysql+aiomysql://u802557144_message:Messenger2026@auth-db2053.hstgr.io:3306/u802557144_messenger?charset=utf8mb4"

async def check_old_server():
    print("=" * 60)
    print("OLD SERVER (auth-db1559) CHECK")
    print("=" * 60)
    
    old_db = Database(OLD_URL)
    try:
        await old_db.connect()
        print("[OK] OLD SERVER SE CONNECT HO GAYA! Data wapas aa sakta hai!")
        
        # Campaigns check karo
        campaigns = await old_db.fetch_all(
            "SELECT id, name, timestamp, total_numbers, sent_success, status FROM campaigns ORDER BY timestamp DESC LIMIT 20"
        )
        
        print(f"\nOld server me campaigns ({len(campaigns)} found):")
        print("-" * 60)
        for c in campaigns:
            print(f"  ID: {c['id']} | {c['timestamp']} | {c['name']} | Total: {c['total_numbers']} | Status: {c['status']}")
        
        # Messages count
        msg_count = await old_db.fetch_one("SELECT COUNT(*) as cnt FROM messages")
        print(f"\nOld server me total messages: {msg_count['cnt']}")
        
        await old_db.disconnect()
        return True, campaigns
        
    except Exception as e:
        print(f"[FAIL] Old server accessible nahi hai: {e}")
        print("\nHostinger ne old server band kar diya hai.")
        await old_db.disconnect()
        return False, []

async def migrate_old_to_new(old_campaigns):
    """Old server se data nikalkar new server me dalo"""
    
    print("\n" + "=" * 60)
    print("NEW SERVER (auth-db2053) SE CONNECT HO RAHA HAI...")
    print("=" * 60)
    
    old_db = Database(OLD_URL)
    new_db = Database(NEW_URL)
    
    try:
        await old_db.connect()
        await new_db.connect()
        print("[OK] Dono servers se connect ho gaya!")
        
        # May 19 ke baad ke campaigns dhundo old server me
        campaigns_to_migrate = await old_db.fetch_all("""
            SELECT * FROM campaigns 
            WHERE timestamp > '2026-05-19 00:00:00'
            ORDER BY timestamp ASC
        """)
        
        print(f"\n19 May ke baad ke campaigns: {len(campaigns_to_migrate)}")
        
        for camp in campaigns_to_migrate:
            camp_dict = dict(camp)
            camp_id = camp_dict['id']
            
            print(f"\nMigrate kar raha hun: {camp_dict['name']} ({camp_dict['timestamp']})")
            
            # Check karo new server me already hai ya nahi
            existing = await new_db.fetch_one(
                "SELECT id FROM campaigns WHERE name = :name AND timestamp = :ts",
                {"name": camp_dict['name'], "ts": camp_dict['timestamp']}
            )
            if existing:
                print(f"  [SKIP] Already exists in new server")
                continue
            
            # Campaign insert karo new server me
            try:
                new_camp_id = await new_db.execute("""
                    INSERT INTO campaigns 
                    (user_id, name, timestamp, total_numbers, sent_success, sent_failed,
                     status, msg_type, template_name, language_code, message_template, 
                     mappings, phone_col, media_url, meta_media_id)
                    VALUES 
                    (:user_id, :name, :timestamp, :total_numbers, :sent_success, :sent_failed,
                     :status, :msg_type, :template_name, :language_code, :message_template,
                     :mappings, :phone_col, :media_url, :meta_media_id)
                """, {
                    "user_id": camp_dict.get('user_id', 1),
                    "name": camp_dict.get('name', ''),
                    "timestamp": camp_dict.get('timestamp'),
                    "total_numbers": camp_dict.get('total_numbers', 0),
                    "sent_success": camp_dict.get('sent_success', 0),
                    "sent_failed": camp_dict.get('sent_failed', 0),
                    "status": camp_dict.get('status', 'completed'),
                    "msg_type": camp_dict.get('msg_type', 'template'),
                    "template_name": camp_dict.get('template_name', ''),
                    "language_code": camp_dict.get('language_code', ''),
                    "message_template": camp_dict.get('message_template', ''),
                    "mappings": camp_dict.get('mappings', ''),
                    "phone_col": camp_dict.get('phone_col', ''),
                    "media_url": camp_dict.get('media_url', ''),
                    "meta_media_id": camp_dict.get('meta_media_id', ''),
                })
                print(f"  [OK] Campaign inserted! New ID: {new_camp_id}")
                
                # Ab is campaign ke messages bhi migrate karo
                messages = await old_db.fetch_all(
                    "SELECT * FROM messages WHERE campaign_id = :cid",
                    {"cid": camp_id}
                )
                print(f"  Messages migrate kar raha hun: {len(messages)}")
                
                if messages:
                    batch = []
                    for msg in messages:
                        msg_dict = dict(msg)
                        batch.append({
                            "user_id": msg_dict.get('user_id', 1),
                            "campaign_id": new_camp_id,
                            "phone": msg_dict.get('phone', ''),
                            "status": msg_dict.get('status', 'delivered'),
                            "error_message": msg_dict.get('error_message', ''),
                            "whatsapp_message_id": msg_dict.get('whatsapp_message_id', ''),
                            "row_data": msg_dict.get('row_data', ''),
                            "timestamp": msg_dict.get('timestamp'),
                        })
                    
                    # 100 ke batch me insert karo
                    for i in range(0, len(batch), 100):
                        await new_db.execute_many("""
                            INSERT INTO messages 
                            (user_id, campaign_id, phone, status, error_message, 
                             whatsapp_message_id, row_data, timestamp)
                            VALUES 
                            (:user_id, :campaign_id, :phone, :status, :error_message,
                             :whatsapp_message_id, :row_data, :timestamp)
                        """, batch[i:i+100])
                    
                    print(f"  [OK] {len(messages)} messages migrate ho gaye!")
                    
            except Exception as e:
                print(f"  [ERROR] Campaign migrate nahi hua: {e}")
        
        await old_db.disconnect()
        await new_db.disconnect()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] MIGRATION COMPLETE!")
        print("Ab Vercel dashboard refresh karo - saara data wapas aa jayega!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")

async def main():
    ok, campaigns = await check_old_server()
    if ok and len(campaigns) > 0:
        print("\nOld server me data mila! Ab migrate karna chahoge?")
        print("Migration automatically shuru ho rahi hai...")
        await migrate_old_to_new(campaigns)
    elif ok:
        print("\nOld server accessible hai lekin campaigns nahi mila.")
    else:
        print("\nOld server accessible nahi hai. CSV wala restore use karna hoga.")

if __name__ == "__main__":
    asyncio.run(main())
