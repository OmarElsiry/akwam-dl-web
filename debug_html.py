import re
import requests

RGX_DL_URL = r'https?://\w*\.*\w+\.\w+/link/\d+'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

url = "https://ak.sv/download/165979/10216/aztec-batman-clash-of-empires"
resp = requests.get(url, headers=HEADERS)
print("Resolved URL:", resp.url)

# Look for high-speed download or similar
links = re.findall(r'href="([^"]*)"', resp.text)
for l in links:
    if "download" in l and l != url:
        print("Found possible link:", l)

# Check the specific regex the user provided
# RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
match = re.search(r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"', resp.text)
if match:
    print("User regex match:", match.group(0))
