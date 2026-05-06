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
        
        try:
            page.evaluate("document.querySelector('a[href*=\"/download/\"]').click()")
        except:
            pass
            
        page.wait_for_timeout(4000)
        
        try:
            page.evaluate("document.querySelector('.link.btn.btn-light').click()")
            page.wait_for_timeout(4000)
        except:
            pass
            
        if not mp4_url:
            print("Did not intercept mp4 url")
            sys.exit(1)
            
        print("Got MP4 URL:", mp4_url)
        
        # GET COOKIES
        pw_cookies = context.cookies()
        cookie_dict = {c['name']: c['value'] for c in pw_cookies}
        print("Cookies:", cookie_dict)
        
        headers = {
            'Referer': 'https://akwam.com.co/',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Dest': 'video',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site'
        }
        
        print("Testing streaming with curl_cffi...")
        resp = requests.get(mp4_url, headers=headers, cookies=cookie_dict, impersonate="chrome120")
        print("Status:", resp.status_code)
        
        if resp.status_code != 200 and resp.status_code != 206:
            print("Body:", resp.text)
        else:
            print("Successfully streamed!")
        
    except Exception as e:
        print("Exception:", e)
        
    browser.close()
