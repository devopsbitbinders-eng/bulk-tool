"""
=============================================================
  CAMPAIGN HISTORY RESTORE SCRIPT
  *** YE SCRIPT KISI KO BHI WHATSAPP MESSAGE NAHI BHEJEGA ***
  Ye sirf aapke database me campaign records wapas save karta hai.
=============================================================

KAISE USE KARE:
1. Niche CAMPAIGNS_TO_RESTORE list me apni details bharo
2. Har campaign ke liye CSV file ka path, date, aur naam daalo
3. Phir terminal me run karo: python scratch/restore_campaigns.py

ZARURI:
- Aapka DATABASE_URL .env file me sahi hona chahiye
- CSV file me phone number ka ek column hona chahiye
"""

import asyncio
import json
import csv
import os
from datetime import datetime
from databases import Database
from dotenv import load_dotenv

# .env file load karo
load_dotenv()

# =====================================================================
# YAHAN APNI CAMPAIGNS KI DETAILS BHARO
# =====================================================================
# user_id: Aapka user ID jo database me hai (niche check karne ka tarika bataya hai)
# Agar pata nahi, to 1 rakhein (aksar admin ka user_id 1 hota hai)

USER_ID = 1  # <-- Agar aapka user ID alag hai to yahan change karo

CAMPAIGNS_TO_RESTORE = [
    
    {
        "name": "Campaign 25 May",
        "date": "2026-05-25 10:00:00",
        "csv_file": r"C:\Users\kajal\Downloads\campaign_139_report.xlsx",  # <-- CSV ka path
        "phone_column": "phone",
        "template_name": "",
        "msg_type": "template",
    },
    {
        "name": "Campaign 26 May",
        "date": "2026-05-26 10:00:00",
        "csv_file": r"C:\Users\kajal\Downloads\campaign_141_report.xlsx",  # <-- CSV ka path
        "phone_column": "phone",
        "template_name": "",
        "msg_type": "template",
    },
   
    
]
# =====================================================================

def normalize_phone(phone_raw):
    """Phone number ko clean karo"""
    if not phone_raw:
        return None
    phone = str(phone_raw).strip().replace(" ", "").replace("-", "").replace("+", "")
    # Remove .0 (Excel numbers se)
    if phone.endswith(".0"):
        phone = phone[:-2]
    if not phone:
        return None
    # India ke liye: agar 10 digit hai to 91 lagao
    if len(phone) == 10 and phone.isdigit():
        phone = "91" + phone
    return phone

def read_csv_file(filepath, phone_col):
    """CSV file padho aur rows return karo"""
    rows = []
    phone_col_lower = phone_col.lower().strip()
    
    # Try different encodings
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                headers = [h.lower().strip() for h in (reader.fieldnames or [])]
                
                # Phone column dhundo
                actual_phone_col = None
                for h in headers:
                    if phone_col_lower in h or 'phone' in h or 'mobile' in h or 'number' in h or 'contact' in h:
                        actual_phone_col = h
                        break
                
                if not actual_phone_col:
                    print(f"   ⚠️  Phone column '{phone_col}' nahi mila. Available columns: {headers}")
                    print(f"   ℹ️  Script pehle column use karega: {headers[0] if headers else 'NONE'}")
                    actual_phone_col = headers[0] if headers else None
                
                for row in reader:
                    # Lowercase keys banao
                    clean_row = {k.lower().strip(): v for k, v in row.items() if k}
                    if actual_phone_col and actual_phone_col in clean_row:
                        rows.append({
                            'phone_raw': clean_row[actual_phone_col],
                            'row_data': clean_row
                        })
            
            print(f"   ✅ File padhi ({encoding}): {len(rows)} rows mili")
            return rows
        except Exception as e:
            continue
    
    print(f"   ❌ File nahi padh saka: {filepath}")
    return []

async def get_user_id(db):
    """Database me users check karo"""
    try:
        users = await db.fetch_all("SELECT id, username, is_admin FROM users LIMIT 10")
        if users:
            print("\n📋 Database me Users:")
            for u in users:
                print(f"   ID: {u['id']} | Username: {u['username']} | Admin: {u['is_admin']}")
            return users[0]['id']  # Pehla user return karo
    except Exception as e:
        print(f"   Users fetch error: {e}")
    return 1

async def restore_campaigns():
    """Main restore function"""
    
    # Database URL
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///campaigns.db")
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://", 1)
    if "charset" not in DATABASE_URL and "mysql" in DATABASE_URL:
        DATABASE_URL += "?charset=utf8mb4"
    
    print(f"\n🔌 Database se connect ho raha hai...")
    print(f"   URL: {DATABASE_URL[:50]}...")
    
    db = Database(DATABASE_URL)
    try:
        await db.connect()
        print("   ✅ Database se connect ho gaya!\n")
    except Exception as e:
        print(f"   ❌ Database connect nahi hua: {e}")
        print("   💡 Check karo ki .env file me DATABASE_URL sahi hai")
        return
    
    # User ID confirm karo
    actual_user_id = await get_user_id(db)
    print(f"\n➡️  USER_ID use hoga: {USER_ID}")
    print(f"   (Agar galat lag raha hai to script me USER_ID change karo)\n")
    print("=" * 60)
    
    total_campaigns_added = 0
    total_messages_added = 0
    
    for i, camp in enumerate(CAMPAIGNS_TO_RESTORE):
        print(f"\n📣 Campaign {i+1}/{len(CAMPAIGNS_TO_RESTORE)}: {camp['name']}")
        print(f"   Date: {camp['date']}")
        print(f"   File: {camp['csv_file']}")
        
        # File exist karta hai?
        if not os.path.exists(camp['csv_file']):
            print(f"   ⚠️  FILE NAHI MILI! Yahan file rakh do: {camp['csv_file']}")
            print(f"   ⏭️  Ye campaign skip kar raha hoon...\n")
            continue
        
        # CSV padho
        rows = read_csv_file(camp['csv_file'], camp.get('phone_column', 'phone'))
        if not rows:
            print(f"   ⚠️  File me koi data nahi mila, skip kar raha hoon...")
            continue
        
        # Valid phones count karo
        valid_phones = []
        for r in rows:
            phone = normalize_phone(r['phone_raw'])
            if phone:
                valid_phones.append({'phone': phone, 'row_data': r['row_data']})
        
        total = len(valid_phones)
        print(f"   📊 Total valid numbers: {total}")
        
        if total == 0:
            print(f"   ⚠️  Koi valid phone number nahi mila, skip kar raha hoon...")
            continue
        
        # Campaign record banao
        try:
            campaign_id = await db.execute("""
                INSERT INTO campaigns 
                (user_id, name, timestamp, total_numbers, sent_success, sent_failed, 
                 status, msg_type, template_name, message_template)
                VALUES 
                (:user_id, :name, :timestamp, :total, :success, :failed, 
                 :status, :msg_type, :template_name, :message_template)
            """, {
                "user_id": USER_ID,
                "name": camp['name'],
                "timestamp": camp['date'],
                "total": total,
                "success": total,  # Sab successfully send ho chuke the
                "failed": 0,
                "status": "completed",
                "msg_type": camp.get('msg_type', 'template'),
                "template_name": camp.get('template_name', ''),
                "message_template": "",
            })
            print(f"   ✅ Campaign record bana! ID: {campaign_id}")
            total_campaigns_added += 1
        except Exception as e:
            print(f"   ❌ Campaign insert error: {e}")
            continue
        
        # Message records banao (batch me)
        messages_to_insert = []
        for r in valid_phones:
            messages_to_insert.append({
                "user_id": USER_ID,
                "campaign_id": campaign_id,
                "phone": r['phone'],
                "status": "delivered",
                "row_data": json.dumps(r['row_data']),
                "error_message": "",
                "timestamp": camp['date'],
            })
        
        # 100 ke batch me insert karo
        batch_size = 100
        inserted = 0
        for j in range(0, len(messages_to_insert), batch_size):
            batch = messages_to_insert[j:j+batch_size]
            try:
                await db.execute_many("""
                    INSERT INTO messages 
                    (user_id, campaign_id, phone, status, row_data, error_message, timestamp)
                    VALUES 
                    (:user_id, :campaign_id, :phone, :status, :row_data, :error_message, :timestamp)
                """, batch)
                inserted += len(batch)
                print(f"   📥 Messages insert ho rahe hain: {inserted}/{total}...", end='\r')
            except Exception as e:
                print(f"\n   ❌ Messages insert error: {e}")
        
        print(f"   ✅ {inserted} message records database me add ho gaye!    ")
        total_messages_added += inserted
    
    await db.disconnect()
    
    print("\n" + "=" * 60)
    print(f"🎉 RESTORE COMPLETE!")
    print(f"   ✅ Campaigns restored: {total_campaigns_added}")
    print(f"   ✅ Message records restored: {total_messages_added}")
    print(f"\n🌐 Ab apna Vercel dashboard open karo aur refresh karo!")
    print(f"   Tumhe saare campaigns aur unki sending history dikh jayegi.")
    print(f"   *** KISI KO BHI WHATSAPP MESSAGE NAHI GAYA HAI ***")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(restore_campaigns())
