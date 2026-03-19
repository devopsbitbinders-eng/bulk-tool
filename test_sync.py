import asyncio
from utils import sync_to_google_sheet

dummy_data = [
    {"phone": "+1234567890", "name": "Test User 1", "delivery status": "Sent", "sent at": "2026-03-17 16:00"},
    {"phone": "+0987654321", "name": "Test User 2", "delivery status": "Failed", "sent at": "2026-03-17 16:01"},
    {"phone": "+1122334455", "name": "Test User 3", "delivery status": "Sent", "sent at": "2026-03-17 16:05"}
]

print("Starting sync test...")
success = sync_to_google_sheet(dummy_data, "messenger_test")
if success:
    print("Sync TEST SUCCESSFUL!")
else:
    print("Sync TEST FAILED!")
