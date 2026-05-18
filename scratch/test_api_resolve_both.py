import requests

BASE_URL = "http://localhost:8000"

print("Testing /api/resolve for le3ba link_id 178067")
r = requests.post(f"{BASE_URL}/api/resolve", json={"url": "go.akwam.com.co/link/178067"})
print(r.status_code, r.text)

print("\nTesting /api/resolve for bloodhounds link_id 143994")
r = requests.post(f"{BASE_URL}/api/resolve", json={"url": "go.akwam.com.co/link/143994"})
print(r.status_code, r.text)
