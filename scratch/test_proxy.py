import httpx
import urllib.request
import certifi

url = "https://tv8.egydead.live/wp-content/uploads/2022/10/%D9%81%D9%8A%D9%84%D9%85-Batman-and-Robin-1997-%D9%85%D8%AA%D8%B1%D8%AC%D9%85-187x280.jpg"

req = urllib.request.Request(
    url, 
    data=None, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://tv8.egydead.live/',
        'Sec-Ch-Ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-origin',
    }
)

try:
    with urllib.request.urlopen(req, timeout=10, cafile=certifi.where()) as response:
        print(f"Status: {response.getcode()}")
        print(f"Content-Type: {response.getheader('Content-Type')}")
except Exception as e:
    print(f"Error: {e}")
