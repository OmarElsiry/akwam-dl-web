"""
Playwright-based extractor for akwam download pages — v2.
Improvements:
- Strict selector: only accept a[download] with href pointing to video CDN (not YouTube etc.)
- Longer wait for the countdown JS (5s instead of 4s)
- Extended navigation timeout (60s)
- Better fallback: scan the page for CDN video links directly
- Retry failed episodes once
- Fix output file path
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

# CDN domains akwam uses for video delivery
VIDEO_CDN_PATTERNS = [
    "downet.net",
    "akw-cdn",
    "akwam-cdn",
    ".mp4",
    ".mkv",
    ".m3u8",
    "cdn.",
    "dl.",
    "files.",
    "stream.",
    "media.",
    "video.",
    "content.",
]

BLACKLISTED_DOMAINS = [
    "youtube.com", "facebook.com", "google.com", "googlesyndication.com",
    "twitter.com", "ak.sv", "akwam.com.co", "akwam.net", "akw.to",
    "histats.com", "javascript", "#", "adsbygoogle",
]


def is_valid_video_url(url: str) -> bool:
    """Returns True if URL looks like a real video file/CDN link, not a social/akwam page."""
    if not url or not url.startswith("http"):
        return False
    for bad in BLACKLISTED_DOMAINS:
        if bad in url:
            return False
    # Must have a CDN pattern or video extension
    return any(p in url for p in VIDEO_CDN_PATTERNS)


async def extract_one(context, ep_name: str, url: str, attempt=1) -> dict:
    """Visit one download page and extract the real file URL after countdown."""
    wait_secs = 5 + (attempt - 1) * 3  # 5s first try, 8s on retry
    print(f"\n[{ep_name}] Attempt {attempt} — wait {wait_secs}s after load")
    
    captured_video = None

    page = await context.new_page()

    async def on_response(resp):
        nonlocal captured_video
        if captured_video:
            return
        u = resp.url
        ct = resp.headers.get("content-type", "")
        if is_valid_video_url(u) or any(x in ct for x in ("video/", "octet-stream")):
            captured_video = u
            print(f"  [NETWORK] {u}")

    page.on("response", on_response)

    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(wait_secs)

        # 1. Check network-intercepted URL first
        if captured_video and is_valid_video_url(captured_video):
            print(f"  [OK-NET] {captured_video}")
            return {"episode": ep_name, "download_page": url, "direct_url": captured_video}

        # 2. a[download] selector — the akwam JS sets href on this after countdown
        direct_link = await page.evaluate("""() => {
            const candidates = [];
            
            // Primary: a[download] — set by countdown JS
            document.querySelectorAll('a[download]').forEach(a => candidates.push(a.href));
            // Secondary: a.download class
            document.querySelectorAll('a.download').forEach(a => candidates.push(a.href));
            // Tertiary: any anchor with video CDN domain
            document.querySelectorAll('a[href]').forEach(a => {
                const h = a.href || '';
                if (h.includes('downet.net') || h.includes('.mp4') || h.includes('.mkv') 
                    || h.includes('cdn') && !h.includes('googlesyndication')) {
                    candidates.push(h);
                }
            });
            
            return candidates.filter(u => u && u.startsWith('http'));
        }""")

        if direct_link:
            valid = [u for u in direct_link if is_valid_video_url(u)]
            if valid:
                print(f"  [OK-JS]  {valid[0]}")
                return {"episode": ep_name, "download_page": url, "direct_url": valid[0]}
            else:
                print(f"  [JS found but invalid] {direct_link[:3]}")

        # 3. Scan page HTML for video URLs
        html = await page.content()
        mp4_matches = re.findall(r'(https?://[^\s"\'<>]+(?:\.mp4|\.mkv|downet\.net)[^\s"\'<>]*)', html)
        valid_mp4 = [u for u in mp4_matches if is_valid_video_url(u)]
        if valid_mp4:
            print(f"  [OK-HTML] {valid_mp4[0]}")
            return {"episode": ep_name, "download_page": url, "direct_url": valid_mp4[0]}

        # 4. Wait more and retry JS check
        print(f"  [WAIT+2s] Countdown may not be done yet...")
        await asyncio.sleep(2)
        direct_link2 = await page.evaluate("""() => {
            const candidates = [];
            document.querySelectorAll('a[download]').forEach(a => { if(a.href) candidates.push(a.href); });
            document.querySelectorAll('a[href*="downet"]').forEach(a => candidates.push(a.href));
            document.querySelectorAll('a[href$=".mp4"]').forEach(a => candidates.push(a.href));
            return candidates.filter(u => u && u.startsWith('http'));
        }""")
        valid2 = [u for u in (direct_link2 or []) if is_valid_video_url(u)]
        if valid2:
            print(f"  [OK-JS2] {valid2[0]}")
            return {"episode": ep_name, "download_page": url, "direct_url": valid2[0]}

        # Screenshot for debugging
        ss_path = f"screenshot_{ep_name.replace(' ', '_')}.png"
        await page.screenshot(path=ss_path, full_page=False)
        print(f"  [FAIL] Screenshot saved: {ss_path}")
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

        for ep_name, url in DOWNLOAD_PAGES:
            result = await extract_one(context, ep_name, url, attempt=1)
            results[ep_name] = result
            await asyncio.sleep(1.5)

        # Retry failures
        failed = [k for k, v in results.items() if not v.get("direct_url")]
        if failed:
            print(f"\n{'='*60}")
            print(f"RETRYING {len(failed)} failed episodes with longer wait...")
            for ep_name, url in DOWNLOAD_PAGES:
                if ep_name in failed:
                    result = await extract_one(context, ep_name, url, attempt=2)
                    results[ep_name] = result
                    await asyncio.sleep(2)

        await browser.close()

    print("\n" + "=" * 70)
    print("FINAL RESULTS — Bloodhounds Season 1")
    print("=" * 70)

    ordered = []
    for ep_name, url in DOWNLOAD_PAGES:
        r = results[ep_name]
        ordered.append(r)
        direct = r.get("direct_url")
        if direct and is_valid_video_url(direct):
            print(f"[OK]   {ep_name}: {direct}")
        elif direct:
            print(f"[WARN] {ep_name}: Got URL but may not be direct: {direct}")
        else:
            print(f"[FAIL] {ep_name}: Could not resolve")

    success = sum(1 for r in ordered if r.get("direct_url") and is_valid_video_url(r.get("direct_url", "")))
    print(f"\n{success}/{len(DOWNLOAD_PAGES)} direct video URLs obtained")

    output_path = "bloodhounds_direct_links.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
