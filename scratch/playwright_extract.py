"""
Playwright-based extractor for akwam download pages.
Opens each page in a real browser, waits for the JS countdown timer (2.2s),
then extracts the actual direct download URL from the revealed button.
"""
import asyncio
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

DOWNLOAD_PAGES = [
    "https://akwam.com.co/download/143999/78413/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-8",
    "https://akwam.com.co/download/143998/78412/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-7",
    "https://akwam.com.co/download/143997/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6",
    "https://akwam.com.co/download/143996/78410/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-5",
    "https://akwam.com.co/download/143995/78409/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-4",
    "https://akwam.com.co/download/143994/78408/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-3",
    "https://akwam.com.co/download/143993/78407/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-2",
    "https://akwam.com.co/download/143992/78406/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-1",
]

# Episode numbers (reversed to match page order: ep8 first)
EP_NAMES = [f"Episode {i}" for i in range(8, 0, -1)]


async def extract_download_url(page, url: str, ep_name: str) -> dict:
    """Visit one download page and extract the real file URL after countdown."""
    print(f"\n[{ep_name}] Opening: {url}")
    
    captured_url = None
    
    # Intercept any network request that looks like a video file or direct download
    async def handle_response(response):
        nonlocal captured_url
        resp_url = response.url
        ct = response.headers.get("content-type", "")
        # Catch video responses or direct file downloads
        if any(ext in resp_url for ext in [".mp4", ".mkv", ".avi", ".webm", ".m3u8"]):
            if not captured_url:
                print(f"  [NETWORK INTERCEPT] Video URL: {resp_url}")
                captured_url = resp_url
        if any(x in ct for x in ["video", "octet-stream"]) and not captured_url:
            print(f"  [NETWORK INTERCEPT] Video Content-Type: {resp_url} ({ct})")
            captured_url = resp_url

    page.on("response", handle_response)

    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        # Wait for countdown to finish (2.2s + buffer)
        await asyncio.sleep(4)
        
        # Try to find the download button (a.download or a[download] or a.btn-download)
        # After countdown the JS sets href on 'a.download'
        selectors_to_try = [
            "a.download",
            "a[download]",
            ".btn-download",
            "a.btn-download",
            ".download-btn a",
            "a.file-name",
            ".file-name a",
            "a[href*='.mp4']",
            "a[href*='.mkv']",
            "a[href*='/dl/']",
            "a[href*='/file/']",
        ]
        
        found_href = None
        for sel in selectors_to_try:
            try:
                el = page.locator(sel).first
                href = await el.get_attribute("href", timeout=2000)
                if href and href.startswith("http") and href != url:
                    print(f"  [SELECTOR {sel}] href = {href}")
                    found_href = href
                    break
            except Exception:
                pass
        
        # If no selector worked, evaluate JS to check for any updated hrefs
        if not found_href:
            result = await page.evaluate("""() => {
                // Check all <a> tags for video file hrefs
                const anchors = Array.from(document.querySelectorAll('a[href]'));
                const videoExts = ['.mp4', '.mkv', '.avi', '.webm', '.m3u8'];
                for (const a of anchors) {
                    const h = a.href || '';
                    if (videoExts.some(ext => h.includes(ext))) return h;
                }
                // Check a.download specifically
                const dlBtn = document.querySelector('a.download');
                if (dlBtn) return dlBtn.href || dlBtn.getAttribute('href') || null;
                // Check for any external non-akwam download link
                const externalDl = anchors.find(a => {
                    const h = a.href || '';
                    return h.startsWith('http') && 
                           !h.includes('akwam.com.co') && 
                           !h.includes('google') && 
                           !h.includes('facebook') &&
                           !h.includes('javascript') &&
                           h.length > 30;
                });
                return externalDl ? externalDl.href : null;
            }""")
            if result:
                print(f"  [JS EVAL] Found href: {result}")
                found_href = result
        
        # If still nothing, get the full page HTML and look for video URLs
        if not found_href and not captured_url:
            html = await page.content()
            import re
            mp4s = re.findall(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', html)
            if mp4s:
                found_href = mp4s[0]
                print(f"  [HTML SCAN] Found .mp4: {found_href}")
        
        final_url = found_href or captured_url
        if final_url:
            print(f"  [OK] {ep_name}: {final_url}")
        else:
            print(f"  [FAIL] Could not extract direct URL for {ep_name}")
            # Take a screenshot for manual inspection
            await page.screenshot(path=f"scratch/screenshot_{ep_name.replace(' ', '_')}.png")
            print(f"  [SCREENSHOT] saved for manual inspection")
        
        return {"episode": ep_name, "download_page": url, "direct_url": final_url}

    except Exception as e:
        print(f"  [ERROR] {ep_name}: {e}")
        return {"episode": ep_name, "download_page": url, "direct_url": None, "error": str(e)}
    finally:
        page.remove_listener("response", handle_response)


async def main():
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

        # Process sequentially to avoid being rate-limited
        for url, ep_name in zip(DOWNLOAD_PAGES, EP_NAMES):
            page = await context.new_page()
            result = await extract_download_url(page, url, ep_name)
            results.append(result)
            await page.close()
            # Small delay between requests
            await asyncio.sleep(1)
        
        await browser.close()
    
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    
    success = 0
    for r in results:
        ep = r["episode"]
        url = r.get("direct_url")
        if url:
            success += 1
            print(f"[OK]   {ep}: {url}")
        else:
            print(f"[FAIL] {ep}: Could not resolve (download page: {r['download_page']})")
    
    print(f"\n{success}/{len(results)} episodes resolved successfully")
    
    # Save results to JSON
    with open("scratch/bloodhounds_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Results saved to scratch/bloodhounds_results.json")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
