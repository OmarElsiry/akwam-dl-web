"""
Deep inspection of Step A page (go.akwam.com.co/link/143999)
to find if it contains the direct file URL in any form.
"""
import sys, re, base64
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '..')
from api.akwam_api import safe_get

html = open('../scratch/debug_step4_a.html', encoding='utf-8').read()

print(f'HTML length: {len(html)}')
print()

# 1. All scripts
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S | re.I)
print(f'Script blocks: {len(scripts)}')

# 2. Find any URL containing a video file extension
video_urls = re.findall(r'(https?://[^\s"\'<>]+\.(?:mp4|mkv|m3u8|ts|avi|webm|mov)[^\s"\'<>]*)', html)
print(f'Direct video URLs: {video_urls[:10]}')

print()
# 3. Look for file hosting patterns (common CDNs used by Arab streaming sites)
cdn_patterns = re.findall(r'(https?://(?:cdn|vid|dl|files?|stream|media)[.\-][^\s"\'<>]{5,})', html)
print('CDN-like URLs:')
for u in cdn_patterns[:15]:
    print(' ', u)

print()
# 4. Look for any base64 encoded content
b64_candidates = re.findall(r'["\']([A-Za-z0-9+/]{60,}={0,2})["\']', html)
print(f'Long base64 candidates: {len(b64_candidates)}')
for b in b64_candidates[:5]:
    try:
        dec = base64.b64decode(b + '==').decode('utf-8', errors='ignore')
        if any(c in dec for c in ['http', '.mp4', '.mkv', 'dl.', 'cdn']):
            print(f'  [DECODED]: {dec[:300]}')
        else:
            print(f'  {b[:60]}...')
    except:
        print(f'  {b[:60]}...')

print()
# 5. Find all script src (external JS files)
ext_scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I)
print('External script files:')
for s in ext_scripts:
    print(' ', s)

print()
# 6. Look for any download-related class/id elements with data attributes
data_elements = re.findall(r'<[^>]+(?:id|class)=["\'][^"\']*(?:download|btn-dl|file)[^"\']*["\'][^>]*>', html, re.I)
print('Download-related HTML elements:')
for e in data_elements[:10]:
    print(' ', e[:200])

print()
# 7. Check all links at the /link/ endpoint page
all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
interesting = [h for h in all_hrefs if not any(x in h for x in ['akwam.com.co', 'facebook', 'youtube', 'javascript', '#', 'ak.sv', 'akw.to'])]
print('Interesting external hrefs:')
for h in interesting[:20]:
    print(' ', h)
