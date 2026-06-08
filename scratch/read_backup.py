import gzip
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

BACKUP_FILE = r"C:\Users\kajal\Downloads\u802557144_messenger.20260529151552.sql.gz"

print("Reading backup file...")

with gzip.open(BACKUP_FILE, 'rt', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print(f"File size: {len(content):,} chars\n")

# Extract ALL campaigns INSERT data
print("=" * 70)
print("ALL CAMPAIGNS IN BACKUP:")
print("=" * 70)

# Find the campaigns INSERT block
camp_match = re.search(
    r"INSERT INTO `campaigns` VALUES\s*([\s\S]+?);\s*(?:--|/\*|$)",
    content,
    re.IGNORECASE
)

if camp_match:
    raw = camp_match.group(1)
    # Each row is (...)
    rows = re.findall(r'\(([^)]+(?:\([^)]*\)[^)]*)*)\)', raw)
    print(f"Total campaigns found: {len(rows)}\n")
    
    for r in rows:
        # Parse: id, name, timestamp, ...
        parts = re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", r)
        if len(parts) >= 3:
            camp_id = parts[0].strip()
            name = parts[1].strip().strip("'")
            ts = parts[2].strip().strip("'")
            total = parts[3].strip() if len(parts) > 3 else '?'
            success = parts[4].strip() if len(parts) > 4 else '?'
            status = parts[6].strip().strip("'") if len(parts) > 6 else '?'
            print(f"  ID: {camp_id:>4} | Date: {ts[:10]} | Success: {success:>6} | Status: {status:10} | Name: {name}")

else:
    print("No campaigns INSERT found, checking differently...")
    # Try to find any campaigns data
    idx = content.find('campaigns')
    print(f"Sample: {content[idx:idx+500]}")

print()
print("=" * 70)
print("MESSAGES COUNT PER CAMPAIGN DATE:")
print("=" * 70)

# Count messages by extracting campaign_ids from messages
msg_matches = re.findall(r"'2026-05-2[0-9] [^']*'", content)
print(f"Messages with May 20-29 dates: {len(msg_matches)}")
if msg_matches:
    for m in msg_matches[:5]:
        print(f"  Sample: {m}")
