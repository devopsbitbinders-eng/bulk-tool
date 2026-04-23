import asyncio
from database import get_db

async def approve_user(username):
    db = await get_db()
    # Check if user exists
    user = await db.fetch_one("SELECT id, is_approved FROM users WHERE username = :u", {"u": username})
    
    if not user:
        print(f"❌ Error: User '{username}' not found.")
        return

    if user['is_approved']:
        print(f"ℹ️ User '{username}' is already approved.")
        return

    await db.execute("UPDATE users SET is_approved = 1 WHERE username = :u", {"u": username})
    print(f"✅ Success: User '{username}' has been approved and can now log in!")

if __name__ == "__main__":
    print("--- Bitbinders Admin Approval Tool ---")
    name = input("Enter the username you want to approve: ").strip()
    if name:
        asyncio.run(approve_user(name))
    else:
        print("❌ No username entered.")
