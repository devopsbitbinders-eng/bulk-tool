import asyncio
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("Testing POST /api/templates/sync")
response = client.post("/api/templates/sync")
print("Response Status:", response.status_code)
print("Response JSON:", response.text)
