import sys
from playwright.sync_api import sync_playwright
from curl_cffi import requests

url = "https://go.akwam.com.co/link/143994"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36',
    )
    page = context.new_page()
    
    mp4_url = None

    def handle_request(request):
        global mp4_url
        if ".mp4" in request.url or ".mkv" in request.url:
            mp4_url = request.url

    page.on("request", handle_request)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        # Click the first download link
        try:
            page.evaluate("document.querySelector('a[href*=\"/download/\"]').click()")
        except:
            print("Failed to click first download link")
            sys.exit(1)
            
        page.wait_for_timeout(4000)
        
        # Click the actual mp4 download button
        try:
            page.evaluate("document.querySelector('.link.btn.btn-light').click()")
            page.wait_for_timeout(4000)
        except:
            print("Failed to click second download link")
            sys.exit(1)
            
        if not mp4_url:
            print("Did not intercept mp4 url")
            sys.exit(1)
            
        print("Got MP4 URL:", mp4_url)
        
        # Now use curl_cffi to stream it
        headers = {
            'Referer': 'https://akwam.com.co/',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Dest': 'video',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site'
        }
        
        print("Testing streaming with curl_cffi...")
        resp = requests.get(mp4_url, headers=headers, impersonate="chrome120", stream=True, timeout=15)
        print("Status:", resp.status_code)
        print("Headers:", resp.headers)
        
        # Also try to read 1 chunk
        if resp.status_code in [200, 206]:
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    print("Successfully streamed chunk of size", len(chunk))
                    break
        else:
            print("Failed. Status:", resp.status_code)
            print("Body:", resp.text)
        
    except Exception as e:
        print("Exception:", e)
        
    browser.close()
