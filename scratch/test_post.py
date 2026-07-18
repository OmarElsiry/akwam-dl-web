"""Test POSTing to the movie URL to see if it returns the players."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
from bs4 import BeautifulSoup

url = 'https://tv8.egydead.live/avatar-3-fire-and-ash-2025-1080p-web-dl/'
print(f"POSTing to {url}")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded'
}
data = {'watch': '1'} # maybe some dummy data? Or just empty POST

response = requests.post(url, headers=headers)
print(f"Status Code: {response.status_code}")
html = response.text

print(f"Raw response length: {len(html)}")

with open('scratch/post_response.html', 'w', encoding='utf-8') as f:
    f.write(html)

soup = BeautifulSoup(html, 'html.parser')

iframes = soup.find_all('iframe')
print(f"Iframes found: {len(iframes)}")
for iframe in iframes:
    print(f"  - {iframe.get('src')}")

# look for server tabs
servers = soup.find_all('ul', class_='serverList')
if not servers:
    servers = soup.find_all('ul', id='servers')
if not servers:
    # generic search for li elements that might be servers
    pass

server_links = soup.select('.serversList li, .watch-servers li, .QualityList li, ul.watchList li') # Guessing class names
if not server_links:
    # Try finding elements with text like Forafile, DoodStream
    for server_name in ['Forafile', 'DoodStream', 'Mixdrop', 'EarnVids', 'StreamHG', 'Vidhide']:
        el = soup.find(text=lambda t: t and server_name.lower() in t.lower())
        if el:
            print(f"Found mention of {server_name}: {el.parent}")

print("Done")
