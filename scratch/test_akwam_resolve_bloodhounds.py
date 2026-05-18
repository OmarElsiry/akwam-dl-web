import requests

BASE_URL = "http://localhost:8000"
link_id = "143994"

print(f"Calling akwam-resolve-stream with link_id {link_id}")
r = requests.get(f"{BASE_URL}/api/akwam-resolve-stream", params={"link_id": link_id})
print(f"Status Code: {r.status_code}")
try:
    print(r.json())
except:
    print(r.text)
