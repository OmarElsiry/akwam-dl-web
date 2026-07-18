"""
Get the full download-li anchor elements and try following them
as a browser would - with proper referrer/cookies.
Also try the /link/ URL with follow_redirects to see if it gives a direct file.
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '..')

import requests

HEADERS_BROWSER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

html = open('../scratch/debug_step4_a.html', encoding='utf-8').read()

# Get the full download-li anchor with all attributes
dl_anchors = re.findall(r'<a[^>]*class=["\'][^"\']*download-li[^"\']*["\'][^>]*>', html, re.I | re.S)
print('Full download-li anchors:')
for a in dl_anchors:
    print(repr(a))
    print()

# Get data attributes from these anchors
for a in dl_anchors:
    data_attrs = re.findall(r'(data-[a-z-]+)=["\']([^"\']*)["\']', a, re.I)
    print('  data attrs:', data_attrs)

print()
# Now look at the hide.js file (may reveal the URL building logic)
print('Fetching akw.to/files/hide.js ...')
try:
    session = requests.Session()
    session.headers.update(HEADERS_BROWSER)
    r = session.get('https://akw.to/files/hide.js', timeout=15)
    print(f'Status: {r.status_code}')
    print('hide.js content (first 3000 chars):')
    print(r.text[:3000])
except Exception as e:
    print(f'Error: {e}')
