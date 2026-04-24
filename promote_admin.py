import asyncio
import os
from database import get_db, init_db

async def promote_user():
    print("--- Bitbinders Admin Promotion Tool ---")
    username = input("Enter the username you want to promote to Admin: ").strip()
    
    if not username:
        print("Error: Username cannot be empty.")
        return

    try:
        db = await get_db()
        # Initialize connection
        await init_db()
        
        # Check if user exists
        user = await db.fetch_one("SELECT id, is_admin FROM users WHERE username = :u", {"u": username})
        
        if not user:
            print(f"Error: User '{username}' not found in the database.")
            return
            
        # Update user to Admin and Approve them
        await db.execute(
            "UPDATE users SET is_admin = 1, is_approved = 1 WHERE username = :u",
            {"u": username}
        )
        
        print(f"Success! '{username}' is now an Approved Administrator.")
        print("They can now see the 'Admin' tab after logging in.")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(promote_user())
