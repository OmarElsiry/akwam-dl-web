"""
Test: Use Playwright's own network context to fetch the MP4 binary.
The theory is that the CDN binds the download token to the browser's
TLS fingerprint + IP + cookies. If we use page.request (the APIRequestContext)
from the SAME browser context that activated the token, it should bypass the 403.
"""
import sys
from playwright.sync_api import sync_playwright
import re as _re

url = "https://go.akwam.com.co/link/143994"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36',
    )
    page = context.new_page()

    try:
        # Step 1: Navigate /link/ page
        print("Step 1: Navigating to /link/ page...")
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        html1 = page.content()

        dl_links = list(dict.fromkeys(
            _re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)
        ))
        if not dl_links:
            print("FAIL: No download links found")
            sys.exit(1)
        print(f"  Found {len(dl_links)} download links")

        # Step 2: Navigate to download page
        download_url = dl_links[0]
        print(f"Step 2: Navigating to download page: {download_url[:60]}...")
        page.goto(download_url, wait_until='domcontentloaded', timeout=30000)

        # Step 3: Wait for JS countdown
        print("Step 3: Waiting 8s for JS countdown...")
        page.wait_for_timeout(8000)

        # Step 4: Extract MP4 URL
        html2 = page.content()
        mp4_matches = _re.findall(r'href=["\']([^"\']+\.mp4)["\']', html2)
        if not mp4_matches:
            mp4_matches = _re.findall(r'href=["\']([^"\']+\.mkv)["\']', html2)
        if not mp4_matches:
            print("FAIL: No MP4 link found after countdown")
            sys.exit(1)

        mp4_url = mp4_matches[0]
        print(f"Step 4: Got MP4 URL: {mp4_url}")

        # ===== TEST A: Use page.evaluate(fetch) inside the browser =====
        print("\n=== TEST A: page.evaluate(fetch) ===")
        try:
            fetch_result = page.evaluate("""async (url) => {
                try {
                    const r = await fetch(url, {
                        method: 'GET',
                        headers: { 'Range': 'bytes=0-1023' },
                        mode: 'cors',
                        credentials: 'include'
                    });
                    const buf = await r.arrayBuffer();
                    return {
                        status: r.status,
                        statusText: r.statusText,
                        contentType: r.headers.get('content-type'),
                        contentLength: r.headers.get('content-length'),
                        bodySize: buf.byteLength,
                        bodyHex: Array.from(new Uint8Array(buf).slice(0, 32)).map(b => b.toString(16).padStart(2, '0')).join('')
                    };
                } catch(e) {
                    return { error: e.message };
                }
            }""", mp4_url)
            print(f"  Result: {fetch_result}")
        except Exception as e:
            print(f"  Exception: {e}")

        # ===== TEST B: Use context.request (APIRequestContext) =====
        print("\n=== TEST B: context.request.get() ===")
        try:
            api_resp = context.request.get(mp4_url, headers={
                "Range": "bytes=0-1023",
                "Referer": download_url,
            })
            print(f"  Status: {api_resp.status}")
            print(f"  Headers: {api_resp.headers}")
            body = api_resp.body()
            print(f"  Body size: {len(body)}")
            if api_resp.status == 200 or api_resp.status == 206:
                print(f"  First 32 bytes hex: {body[:32].hex()}")
                print("  SUCCESS!")
            else:
                print(f"  Body text: {body[:500]}")
        except Exception as e:
            print(f"  Exception: {e}")

        # ===== TEST C: Navigate the browser directly to the MP4 URL =====
        # This simulates what happens when a user clicks the download link
        print("\n=== TEST C: page.goto(mp4_url) - direct navigation ===")
        try:
            captured = [None]
            def capture_response(response):
                if ".mp4" in response.url and response.status in (200, 206):
                    captured[0] = response
            page.on("response", capture_response)

            page.goto(mp4_url, wait_until='commit', timeout=15000)
            print(f"  Page URL after nav: {page.url[:80]}")
            mp4_response = captured[0]
            if mp4_response:
                print(f"  Response status: {mp4_response.status}")
                print(f"  Response headers: {mp4_response.headers}")
                body = mp4_response.body()
                print(f"  Body size: {len(body)}")
                print(f"  First 32 bytes hex: {body[:32].hex()}")
                print("  SUCCESS!")
            else:
                print("  No mp4 response captured")
        except Exception as e:
            print(f"  Exception: {e}")

    except Exception as e:
        print(f"EXCEPTION: {e}")

    browser.close()
