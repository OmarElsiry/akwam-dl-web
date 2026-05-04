import sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '..')
from api.akwam_api import safe_get, RGX_SHORTEN_URL, RGX_DIRECT_URL

HTTP = 'https://'

# From step A debug: we saw these download links:
# 1. akwam.com.co/download/...  (main - JS-gated)
# 2. two.akw.cam/download/...   (alternative CDN!)

link_id = 'go.akwam.com.co/link/143999'
url1 = HTTP + link_id
r1 = safe_get(url1)
html1 = r1.content.decode('utf-8', errors='replace')

# Get ALL unique download URLs from step A
all_dl = re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)
unique_dl = list(dict.fromkeys(all_dl))  # deduplicate preserving order
print('All unique download hrefs from step A page:')
for u in unique_dl:
    print(' ', u)

print()
# Try each alternative download URL
for dl_url in unique_dl:
    print(f'\n--- Trying: {dl_url}')
    try:
        r = safe_get(dl_url, allow_redirects=True)
        print(f'    Status: {r.status_code}  Final URL: {r.url}')
        ct = r.headers.get('content-type', '')
        cl = r.headers.get('content-length', '?')
        print(f'    Content-Type: {ct}  Content-Length: {cl}')
        
        if 'video' in ct or 'octet-stream' in ct or 'mp4' in ct:
            print('    [DIRECT VIDEO LINK!]', r.url)
        else:
            # Check if final URL is a video
            if '.mp4' in r.url or '.mkv' in r.url:
                print('    [VIDEO URL in redirect!]', r.url)
            else:
                html_r = r.content.decode('utf-8', errors='replace')[:500]
                print('    Response snippet:', repr(html_r))
    except Exception as ex:
        print(f'    Error: {ex}')
