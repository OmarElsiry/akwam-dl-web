import requests, re

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
})

# Step 1: Visit the download page (this sets cookies and generates a fresh token)
dl_page_url = 'https://akwam.com.co/download/143994/78408/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-3'
r1 = session.get(dl_page_url, timeout=15)
print('Step 1 - Download page status:', r1.status_code)
print('Cookies:', dict(session.cookies))

# Extract the fresh mp4 URL
mp4s = re.findall(r'href=["\']([^"\']+\.mp4)["\']', r1.text)
print('MP4 URLs from page:', mp4s)

if mp4s:
    fresh_url = mp4s[0]
    print('\nStep 2 - Trying fresh URL with same session cookies...')
    
    # Try with same session (cookies preserved)
    r2 = session.get(fresh_url, stream=True, timeout=15)
    print(f'Status: {r2.status_code}, CT: {r2.headers.get("content-type")}, CL: {r2.headers.get("content-length")}')
    r2.close()

    # Try also setting Referer to the download page
    print('\nStep 3 - Same session + Referer to download page...')
    r3 = session.get(fresh_url, stream=True, timeout=15, headers={
        'Referer': dl_page_url,
    })
    print(f'Status: {r3.status_code}, CT: {r3.headers.get("content-type")}, CL: {r3.headers.get("content-length")}')
    r3.close()

# Also look for any other download mechanism in the page
# Maybe there's an AJAX endpoint or form submission
print('\n--- Looking for AJAX/form patterns ---')
ajax = re.findall(r'(?:fetch|XMLHttpRequest|axios|ajax)\s*\(?\s*["\']([^"\']+)', r1.text)
print('AJAX calls:', ajax[:5])

forms = re.findall(r'<form[^>]*action=["\']([^"\']+)["\']', r1.text)
print('Form actions:', forms[:5])

# Look for the download button mechanism
download_btns = re.findall(r'id=["\']download["\'][^>]*', r1.text)
print('Download buttons:', download_btns[:3])

# Check for any JS countdown/timer mechanism
timers = re.findall(r'(?:setTimeout|setInterval|countdown|timer)\s*\([^)]*\)', r1.text)
print('Timer JS:', timers[:3])

# Look at script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', r1.text, re.DOTALL)
for i, s in enumerate(scripts):
    if 'download' in s.lower() or 'mp4' in s.lower() or 'redirect' in s.lower():
        print(f'\n--- Script {i} (relevant) ---')
        print(s[:500])
