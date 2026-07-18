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
            html2 = page.content()
            with open("scratch/ep3_download_page.html", "w", encoding="utf-8") as f:
                f.write(html2)
            print("Saved download page HTML")
    except Exception as e:
        print("Exception:", e)
        
    browser.close()
