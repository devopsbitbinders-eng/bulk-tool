import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        res = await client.get("https://spread.bitbinders.in/")
        print("Status:", res.status_code)
        print("Text:", res.text[:500])

asyncio.run(test())
