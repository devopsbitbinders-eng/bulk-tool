import asyncio
import httpx

async def test():
    webhook_url = "https://script.google.com/macros/s/AKfycby_c47e9Vo28bZr3Bk3nvU7oUdAMZZ5Oydj5_uNbqejI7Szl71C2-n3gdHrPs9xDYdbrg/exec"
    payload = {
        "phone": "918009521111",
        "status": "delivered",
        "campaign_name": "Test Campaign"
    }
    
    print(f"Sending POST to {webhook_url}")
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(webhook_url, json=payload)
            print(f"Status Code: {response.status_code}")
            print(f"Response URL: {response.url}")
            print(f"Response Text: {response.text[:500]}")
    except Exception as e:
        print(f"Exception occurred: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
