import requests

url = 'https://s301d5.downet.net/download/1778044982/69f97eb691bb0/Bloodhounds.S01E03.720p.WEB-DL.AKWAM.mp4'

# Test different referer values to find which one the CDN accepts
referers = [
    'https://akwam.com.co/',
    'https://akwam.com.co/download/143994/78408/bloodhounds',
    'https://s301d5.downet.net/',
    'https://downet.net/',
    None,  # no referer
]

for ref in referers:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'identity;q=1, *;q=0',
        'Connection': 'keep-alive',
    }
    if ref:
        headers['Referer'] = ref
        headers['Origin'] = ref.rstrip('/')
    
    r = requests.get(url, headers=headers, stream=True, timeout=15, allow_redirects=True)
    ct = r.headers.get('content-type', 'none')
    cl = r.headers.get('content-length', 'none')
    print(f'Referer: {ref!r:60s} => Status: {r.status_code}, CT: {ct}, CL: {cl}')
    r.close()

# Also test Range request like a video player would
print('\n--- Range request test ---')
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://akwam.com.co/',
    'Range': 'bytes=0-1024',
}
r = requests.get(url, headers=headers, stream=True, timeout=15)
print(f'Range Status: {r.status_code}, CT: {r.headers.get("content-type")}, CL: {r.headers.get("content-length")}')
r.close()
