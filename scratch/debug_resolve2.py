import sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '..')

from api.akwam_api import safe_get, RGX_SHORTEN_URL, RGX_DIRECT_URL

HTTP = 'https://'
link_id = 'go.akwam.com.co/link/143999'
url1 = HTTP + link_id
print('Step A: GET', url1)
r1 = safe_get(url1)
print('Status:', r1.status_code, ' Final URL:', r1.url)
html1 = r1.content.decode('utf-8', errors='replace')
open('debug_step4_a.html', 'w', encoding='utf-8').write(html1)
print('Saved (len=%d)' % len(html1))

m1 = re.search(RGX_SHORTEN_URL, html1)
print('RGX_SHORTEN_URL match:', m1)

broad_dl = re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)
print('Broad /download/ hrefs:', broad_dl[:5])

broad_all = re.findall(r'href="(https?://[^"]{10,80})"', html1)
print('All hrefs first 10:', broad_all[:10])

if m1:
    short_url = HTTP + m1.group(1)
    print('\nStep B: GET', short_url)
    r2 = safe_get(short_url)
    print('Status:', r2.status_code, ' Final URL:', r2.url)
    html2 = r2.content.decode('utf-8', errors='replace')
    open('debug_step4_b.html', 'w', encoding='utf-8').write(html2)
    print('Saved (len=%d)' % len(html2))

    m2 = re.search(RGX_DIRECT_URL, html2)
    print('RGX_DIRECT_URL match:', m2)

    dl_links = re.findall(r'href="(https?://[^"]+)"[^>]*download', html2)
    print('Anchors with download attr:', dl_links[:5])

    mp4_links = re.findall(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', html2)
    print('.mp4 links:', mp4_links[:5])
