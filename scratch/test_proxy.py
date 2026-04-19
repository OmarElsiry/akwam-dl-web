import httpx
import urllib.parse

orig_url = "https://tv8.egydead.live/wp-content/uploads/2022/10/%D9%81%D9%8A%D9%84%D9%85-Batman-and-Robin-1997-%D9%85%D8%AA%D8%B1%D8%AC%D9%85-187x280.jpg"
encoded_url = urllib.parse.quote(orig_url)
wsrv_url = f"https://wsrv.nl/?url={encoded_url}&w=120&h=170&fit=cover&output=webp"

r = httpx.get(wsrv_url, follow_redirects=True, timeout=10)

print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('content-type', 'N/A')}")
print(f"Content-Length: {len(r.content)}")
print(f"First 20 bytes: {r.content[:20]}")
