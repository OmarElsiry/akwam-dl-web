import sys
from playwright.sync_api import sync_playwright
import re as _re

url = "https://go.akwam.com.co/link/143994"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel="chrome")
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    )
    page = context.new_page()

    tracing_enabled = False

    def handle_request(request):
        if tracing_enabled and (".mp4" in request.url or ".mkv" in request.url):
            print("->", request.method, request.url)
            for k, v in request.headers.items():
                if k.lower() in ('referer', 'cookie', 'sec-ch-ua'):
                    print(f"   {k}: {v}")

    def handle_response(response):
        if tracing_enabled and (".mp4" in response.url or ".mkv" in response.url):
            print("<-", response.status, response.url)

    context.on("request", handle_request)
    context.on("response", handle_response)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        html1 = page.content()
        dl_links = list(dict.fromkeys(_re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)))
        
        if not dl_links:
            print("No download link found!")
            sys.exit(1)
            
        download_url = dl_links[0]
        print("Goto:", download_url)
        page.goto(download_url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(4000)
        
        print("Enabling trace and clicking final download button...")
        tracing_enabled = True
        try:
            page.evaluate("""
                var btn = document.querySelector('.link.btn.btn-light');
                if(btn) {
                    btn.removeAttribute('target');
                }
            """)
            page.locator('.link.btn.btn-light').click(force=True)
            page.wait_for_timeout(5000)
        except Exception as e:
            print("Click failed:", e)
            
    except Exception as e:
        print("Exception:", e, file=sys.stderr)
        
    browser.close()
