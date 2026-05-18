import requests
import time

BASE_URL = "http://localhost:8000"

def test_stream(link_id, name):
    t0 = time.time()
    print(f"Testing {name} with link_id {link_id}")
    r = requests.get(f"{BASE_URL}/api/akwam-resolve-stream", params={"link_id": link_id})
    t1 = time.time()
    print(f"[{name}] Status: {r.status_code}, Time: {t1-t0:.2f}s")
    print(r.json() if r.status_code == 200 else r.text)

test_stream("178067", "le3ba")
test_stream("143994", "bloodhounds")
