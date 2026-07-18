"""
Playwright-based extractor for akwam download pages — v3.
Tighter URL validation: only accept actual video files (not thumbnails).
Uses a layered approach:
  1. Wait for 'a[download]' element to get a real href
  2. Network intercept specifically for .mp4/.mkv responses  
  3. JS poll the download button href every 500ms for up to 8s
"""
import asyncio
import sys
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

DOWNLOAD_PAGES = [
    ("Episode 8", "https://akwam.com.co/download/143999/78413/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-8"),
    ("Episode 7", "https://akwam.com.co/download/143998/78412/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-7"),
    ("Episode 6", "https://akwam.com.co/download/143997/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6"),
    ("Episode 5", "https://akwam.com.co/download/143996/78410/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-5"),
    ("Episode 4", "https://akwam.com.co/download/143995/78409/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-4"),
    ("Episode 3", "https://akwam.com.co/download/143994/78408/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-3"),
    ("Episode 2", "https://akwam.com.co/download/143993/78407/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-2"),
    ("Episode 1", "https://akwam.com.co/download/143992/78406/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-1"),
]

VIDEO_EXTS = (".mp4", ".mkv", ".avi", ".webm", ".m3u8", ".ts")


def is_real_video(url: str) -> bool:
    """True only if URL ends in a video extension or has /download/ path + CDN server."""
    if not url or not url.startswith("http"):
        return False
    u = url.lower()
    # Must have video extension OR be a CDN download path
    has_ext = any(u.endswith(ext) or (ext + "?") in u for ext in VIDEO_EXTS)
    has_dl_path = "/download/" in u and not "akwam.com.co" in u  # exclude the countdown page itself
    # Not a thumbnail/image
    is_image = any(x in u for x in ["/thumb/", "/uploads/", ".jpg", ".png", ".webp", ".gif"])
    return (has_ext or has_dl_path) and not is_image


async def poll_for_download_href(page, timeout_s=10) -> str | None:
    """Poll the page every 500ms for up to timeout_s seconds for a valid download href."""
    for _ in range(timeout_s * 2):
        href = await page.evaluate("""() => {
            // a[download] is set by the countdown JS
            const el = document.querySelector('a[download]');
            if (el && el.href && el.href !== '' && !el.href.endsWith('#')) return el.href;
            // Also try a.download (class)
            const el2 = document.querySelector('a.download');
            if (el2 && el2.href && el2.href !== '' && !el2.href.endsWith('#')) return el2.href;
            return null;
        }""")
        if href and is_real_video(href):
            return href
        await asyncio.sleep(0.5)
    return None


async def extract_one(context, ep_name: str, url: str, attempt=1) -> dict:
    print(f"\n[{ep_name}] Attempt {attempt}")

    captured_video = None
    page = await context.new_page()

    async def on_response(resp):
        nonlocal captured_video
        if captured_video:
            return
        u = resp.url
        ct = resp.headers.get("content-type", "")
        if is_real_video(u) or "video/" in ct:
            captured_video = u
            print(f"  [NETWORK] {u}")

    page.on("response", on_response)

    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")

        # Poll for the download button href (set by countdown JS)
        print(f"  Polling for download href (up to 10s)...")
        href = await poll_for_download_href(page, timeout_s=10)

        if href and is_real_video(href):
            print(f"  [OK-POLL] {href}")
            return {"episode": ep_name, "download_page": url, "direct_url": href}

        # Check network-intercepted
        if captured_video and is_real_video(captured_video):
            print(f"  [OK-NET]  {captured_video}")
            return {"episode": ep_name, "download_page": url, "direct_url": captured_video}

        # Scan HTML for .mp4 patterns
        html = await page.content()
        mp4_matches = re.findall(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', html)
        valid = [u for u in mp4_matches if is_real_video(u)]
        if valid:
            print(f"  [OK-HTML] {valid[0]}")
            return {"episode": ep_name, "download_page": url, "direct_url": valid[0]}

        # Log what we see on the page for debugging
        all_hrefs = await page.evaluate("""() => 
            Array.from(document.querySelectorAll('a[href]')).map(a => a.href).filter(h => h && h.startsWith('http'))
        """)
        non_akwam = [h for h in all_hrefs if "akwam" not in h and "google" not in h and "facebook" not in h]
        print(f"  [DEBUG] Non-akwam hrefs: {non_akwam[:5]}")
        print(f"  [DEBUG] a[download] value: {href!r}")

        ss = f"screenshot_{ep_name.replace(' ', '_')}_attempt{attempt}.png"
        await page.screenshot(path=ss)
        print(f"  [FAIL] Screenshot saved: {ss}")
        return {"episode": ep_name, "download_page": url, "direct_url": None}

    except Exception as e:
        print(f"  [ERROR] {e}")
        return {"episode": ep_name, "download_page": url, "direct_url": None, "error": str(e)}
    finally:
        page.remove_listener("response", on_response)
        await page.close()


async def main():
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

        # First pass
        for ep_name, url in DOWNLOAD_PAGES:
            r = await extract_one(context, ep_name, url, attempt=1)
            results[ep_name] = r
            await asyncio.sleep(1.5)

        # Retry failures
        failed = [(ep, url) for ep, url in DOWNLOAD_PAGES if not results[ep].get("direct_url")]
        if failed:
            print(f"\n{'='*60}")
            print(f"RETRYING {len(failed)} failed episodes...")
            for ep_name, url in failed:
                r = await extract_one(context, ep_name, url, attempt=2)
                results[ep_name] = r
                await asyncio.sleep(2)

        await browser.close()

    print("\n" + "=" * 70)
    print("FINAL RESULTS — Bloodhounds Season 1 (720p)")
    print("=" * 70)
    ordered = []
    for ep_name, url in DOWNLOAD_PAGES:
        r = results[ep_name]
        ordered.append(r)
        direct = r.get("direct_url")
        if direct and is_real_video(direct):
            print(f"[OK]   {ep_name}:\n       {direct}")
        else:
            print(f"[FAIL] {ep_name}: {direct or 'No URL found'}")

    success = sum(1 for r in ordered if r.get("direct_url") and is_real_video(r.get("direct_url", "")))
    print(f"\n{success}/{len(DOWNLOAD_PAGES)} direct video URLs obtained")

    with open("bloodhounds_direct_links.json", "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
    print("Saved to bloodhounds_direct_links.json")

    # Print plain URL list for easy copy-paste
    print("\n--- PLAIN URL LIST ---")
    for r in ordered:
        d = r.get("direct_url")
        if d and is_real_video(d):
            print(d)


if __name__ == "__main__":
    asyncio.run(main())
