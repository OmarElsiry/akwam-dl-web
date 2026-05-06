import sys
from playwright.sync_api import sync_playwright

url = "https://go.akwam.com.co/link/143994"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # Perfect Chrome 120 match
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        extra_http_headers={
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'accept-language': 'en-US,en;q=0.9',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1'
        }
    )
    
    # We must also mock navigator.webdriver = false
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    page = context.new_page()

    tracing_enabled = False

    def handle_response(response):
        if tracing_enabled and (".mp4" in response.url or ".mkv" in response.url):
            print("<-", response.status, response.url)
            if response.status == 403:
                print(response.text()[:200])

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        try:
            page.evaluate("document.querySelector('a[href*=\"/download/\"]').click()")
        except:
            pass
            
        page.wait_for_timeout(4000)
        
        print("Enabling trace and clicking final download button...")
        tracing_enabled = True
        try:
            page.evaluate("document.querySelector('.link.btn.btn-light').click()")
            page.wait_for_timeout(5000)
        except Exception as e:
            print("Click failed:", e)
            
    except Exception as e:
        print("Exception:", e, file=sys.stderr)
        
    browser.close()
