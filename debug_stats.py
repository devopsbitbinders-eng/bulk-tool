import asyncio
import os
import sys

# Add current dir to path
sys.path.append('c:/Users/kajal/Downloads/messanger')

# Mock FastAPI Request if needed, but not for get_dashboard_stats
from main import get_dashboard_stats

async def main():
    try:
        print("Starting stats test...")
        stats = await get_dashboard_stats()
        print("SUCCESS:", stats)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
