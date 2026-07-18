"""
Try POST to the akwam download page to get the direct file URL,
mimicking what the browser JS does after the countdown timer.
Also check if there's a token/nonce in the page we need to pass.
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '..')
from api.akwam_api import safe_get

import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar,en;q=0.9',
    'Referer': 'https://go.akwam.com.co/link/143999',
}

# First get the step-A page and collect cookies
session = requests.Session()
session.headers.update(HEADERS)

url_a = 'https://go.akwam.com.co/link/143999'
print(f'GET {url_a}')
r1 = session.get(url_a, timeout=30)
print(f'Status: {r1.status_code}  Cookies: {dict(session.cookies)}')
html1 = r1.text

# Check for CSRF token or _token field
tokens = re.findall(r'(?:_token|csrf)["\'][^>]*value=["\']([^"\']+)["\']', html1, re.I)
tokens += re.findall(r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']', html1, re.I)
print(f'CSRF tokens: {tokens}')

# Now try the download URL with session cookies + referer
dl_url = 'https://akwam.com.co/download/143999/78413/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-8'

session.headers['Referer'] = url_a
print(f'\nGET (with cookies+referer) {dl_url}')
r2 = session.get(dl_url, timeout=30, allow_redirects=True)
print(f'Status: {r2.status_code}  Final URL: {r2.url}')
ct = r2.headers.get('content-type', '')
print(f'Content-Type: {ct}')
if 'video' in ct or 'octet' in ct:
    print('[DIRECT VIDEO!]', r2.url)
else:
    # Look for the actual file link in the response
    html2 = r2.text
    # Check for a link that ends in .mp4 or similar
    file_links = re.findall(r'(https?://[^\s"\'<>]+\.(?:mp4|mkv|avi|webm)[^\s"\'<>]*)', html2)
    print('Video file links:', file_links[:5])
    
    # Check for a data-file or data-url attribute  
    data_file = re.findall(r'data-(?:file|url|src|href)=["\']([^"\']+)["\']', html2)
    print('data-file/url attrs:', data_file[:5])

    # Any redirect hints
    redir = re.findall(r'(?:window\.location|location\.href)\s*=\s*["\']([^"\']+)["\']', html2)
    print('JS redirects:', redir[:5])

    # Try sending a POST (some sites use POST to get the actual download)
    print(f'\nPOST to {dl_url}')
    r3 = session.post(dl_url, timeout=30, allow_redirects=True)
    print(f'Status: {r3.status_code}  Final URL: {r3.url}')
    ct3 = r3.headers.get('content-type', '')
    print(f'Content-Type: {ct3}')
    if 'video' in ct3 or 'octet' in ct3:
        print('[DIRECT VIDEO!]', r3.url)
    else:
        html3 = r3.text
        file3 = re.findall(r'(https?://[^\s"\'<>]+\.(?:mp4|mkv|avi|webm)[^\s"\'<>]*)', html3)
        print('Video file links in POST resp:', file3[:5])
        print('POST response snippet:', repr(html3[:300]))
