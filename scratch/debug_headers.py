import traceback
from playwright.sync_api import sync_playwright
import re as _re

url = 'https://go.akwam.com.co/link/143994'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36',
    )
    page = context.new_page()

    def handle_request(request):
        if "s30" in request.url or "downet.net" in request.url or ".mp4" in request.url:
            print("Found request:", request.url)
            print("Method:", request.method)
            print("Headers:")
            for k, v in request.headers.items():
                print(f"  {k}: {v}")

    page.on("request", handle_request)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        html1 = page.content()

        dl_links = list(dict.fromkeys(
            _re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)
        ))
        if dl_links:
            download_url = dl_links[0]
            print("Navigating to download page:", download_url)
            page.goto(download_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(4000)

            try:
                print("Evaluating JS to click the download link...")
                page.evaluate("document.querySelector('.link.btn.btn-light').click()")
                page.wait_for_timeout(10000)
            except Exception as e:
                print("Could not click download button:", str(e))
                
    except Exception as e:
        print("Exception:", e)
        
    browser.close()
