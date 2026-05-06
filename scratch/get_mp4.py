import traceback
import sys
from playwright.sync_api import sync_playwright

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
        
        # Click the download link
        try:
            page.evaluate("document.querySelector('a[href*=\"/download/\"]').click()")
        except:
            print("Failed to click first download link", file=sys.stderr)
            sys.exit(1)
            
        page.wait_for_timeout(4000)
        
        try:
            page.evaluate("document.querySelector('.link.btn.btn-light').click()")
            page.wait_for_timeout(5000)
        except:
            print("Failed to click second download link", file=sys.stderr)
            sys.exit(1)
            
        if not mp4_url:
            print("Did not intercept mp4 url", file=sys.stderr)
            sys.exit(1)
            
        print("Got MP4 URL:", mp4_url)
        
    except Exception as e:
        print("Exception:", e, file=sys.stderr)
        
    browser.close()
