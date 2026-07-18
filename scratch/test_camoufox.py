import sys
import time
from camoufox.sync_api import Camoufox

url = "https://go.akwam.com.co/link/143994"

with Camoufox(headless=True) as browser:
    page = browser.new_page()
    
    mp4_url = None

    def handle_request(request):
        global mp4_url
        if ".mp4" in request.url or ".mkv" in request.url:
            mp4_url = request.url

    page.on("request", handle_request)

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
    
    # Try fetching a chunk of the mp4 using camoufox's context!
    # Wait, can we fetch using page.evaluate?
    print("Fetching MP4 chunk using page.request...")
    
    req_context = browser.request
    resp = req_context.get(
        mp4_url, 
        headers={
            "Referer": "https://akwam.com.co/",
            "Range": "bytes=0-100"
        }
    )
    
    print("Status:", resp.status)
    print("Headers:", resp.headers)
    if resp.status == 403:
        print("Body:", resp.text())
        
    # Wait, wait! Playwright's `browser.request.get` might not use the same context cookies or stealth!
    # A better way is to use page.evaluate(fetch)
    print("\nFetching using page.evaluate fetch:")
    status = page.evaluate("""async (url) => {
        let r = await fetch(url, {
            headers: {"Range": "bytes=0-100"}
        });
        return r.status;
    }""", mp4_url)
    print("Status via fetch:", status)
