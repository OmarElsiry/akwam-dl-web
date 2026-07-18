"""
FINAL TEST: Intercept the actual download that happens when we click
the download button on the Akwam countdown page. The browser itself
is the one initiating the request, so if the CDN blocks even the
headless Chromium browser on this IP, then no server-side solution works
and we MUST redirect to the user's browser.

This test also checks: does the CDN 403 even the headless browser navigation?
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

    # Capture ALL network responses
    responses = []
    def log_response(response):
        responses.append({
            'url': response.url[:100],
            'status': response.status,
            'ct': response.headers.get('content-type', ''),
        })
        # Print mp4/mkv/downet responses specifically
        if 'downet.net' in response.url or '.mp4' in response.url:
            print(f"  [RESPONSE] {response.status} {response.url[:100]} CT={response.headers.get('content-type','')}")
    page.on("response", log_response)

    try:
        # Step 1: Navigate to /link/ page
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
        print(f"Step 2: Navigating to download page...")
        page.goto(download_url, wait_until='domcontentloaded', timeout=30000)

        # Step 3: Wait for JS countdown
        print("Step 3: Waiting 8s for JS countdown...")
        page.wait_for_timeout(8000)

        # Step 4: Find and click the download button
        html2 = page.content()
        mp4_matches = _re.findall(r'href=["\']([^"\']+\.mp4)["\']', html2)
        if mp4_matches:
            mp4_url = mp4_matches[0]
            print(f"Step 4: Found MP4 URL in page: {mp4_url}")
        else:
            print("Step 4: FAIL - no mp4 link in page")
            sys.exit(1)

        # Step 5: Try clicking the download button and intercepting the download
        print("Step 5: Clicking download button to trigger actual browser download...")

        # Set up download handling
        try:
            with page.expect_download(timeout=15000) as download_info:
                # Click the download link
                page.evaluate("""(mp4_url) => {
                    const link = document.querySelector('a[href*=".mp4"]');
                    if (link) {
                        link.click();
                    } else {
                        // Try navigating directly
                        window.location.href = mp4_url;
                    }
                }""", mp4_url)
            
            download = download_info.value
            print(f"  Download started! Suggested filename: {download.suggested_filename}")
            print(f"  Download URL: {download.url[:100]}")
            
            # Save a small piece to verify
            path = download.path()
            if path:
                with open(path, 'rb') as f:
                    chunk = f.read(1024)
                print(f"  First 32 bytes: {chunk[:32].hex()}")
                print("  SUCCESS! Download works from headless browser!")
            download.cancel()

        except Exception as e:
            print(f"  Download failed or timed out: {e}")
            
            # Step 6: As a final test, just navigate the browser directly to the mp4
            print("\nStep 6: Direct browser navigation to MP4 URL...")
            new_page = context.new_page()
            
            resp_captured = [None]
            def cap(r):
                resp_captured[0] = r
            new_page.on("response", lambda r: cap(r) if '.mp4' in r.url else None)
            
            try:
                new_page.goto(mp4_url, wait_until='commit', timeout=15000)
            except:
                pass
            
            if resp_captured[0]:
                r = resp_captured[0]
                print(f"  Status: {r.status}")
                print(f"  Content-Type: {r.headers.get('content-type','')}")
                if r.status == 403:
                    print("  CONFIRMED: CDN blocks even real browser on this IP!")
                    print("  The ONLY solution is client-side redirect.")
                elif r.status in (200, 206):
                    print("  SUCCESS: Browser can access the file!")
            else:
                print("  No response captured")
            new_page.close()

        # Print all captured responses summary
        print(f"\n--- All {len(responses)} responses ---")
        for r in responses:
            if 'downet' in r['url'] or '.mp4' in r['url'] or r['status'] >= 400:
                print(f"  {r['status']} {r['url']} [{r['ct']}]")

    except Exception as e:
        print(f"EXCEPTION: {e}")

    browser.close()
