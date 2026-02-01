import os
import sys
import json
import time
import requests
from playwright.sync_api import sync_playwright
from egydead_dl import EgyDeadDL

# Output file for collected URLs
URLS_FILE = "test_urls.json"
RESULTS_FILE = "test_results.txt"

def gather_test_cases():
    print("Gathering test cases...", flush=True)
    dl = EgyDeadDL()
    
    # Queries to ensure variety
    queries = ["spy x family"] 
    collected_urls = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for q in queries:
            print(f"Searching for: {q}", flush=True)
            results = dl.search(q)
            if not results: continue
            
            # Pick first result
            item = results[0]
            print(f"Checking item: {item['title']}")
            
            # If TV series, get an episode
            url_to_scrape = item['url']
            if "/series/" in item['url']:
                 resp = requests.get(item['url'], headers=dl.headers)
                 eps = dl.get_episode_links(resp.text) # Assuming this method exists or similar logic
                 if not eps:
                    # manual regex fallback if get_episode_links isn't available/working
                    import re
                    eps = re.findall(r'href="([^"]*/episode/[^"]+)"', resp.text)
                 
                 if eps:
                     url_to_scrape = eps[0] # Take first episode
            
            print(f"Scraping servers from: {url_to_scrape}")
            
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto(url_to_scrape, timeout=30000, wait_until="domcontentloaded")
                
                # Click Watch Button
                try:
                    btn = page.locator(".watchNow button").or_(page.locator("text='المشاهده والتحميل'")).first
                    if btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(2000)
                except: pass
                
                # Scrape Links
                page.wait_for_timeout(2000) # Wait for JS
                links = page.evaluate("""() => {
                    const res = [];
                    document.querySelectorAll('.downloadv-item, .ser-link, li.download-item a').forEach(a => {
                        res.push({txt: a.innerText, href: a.href});
                    });
                     if (res.length === 0) {
                         document.querySelectorAll('a').forEach(a => {
                             if(a.href && (a.href.includes('hglink') || a.href.includes('uptobox'))) {
                                 res.push({txt: a.innerText || 'Unknown', href: a.href});
                             }
                         });
                     }
                    return res;
                }""")
                
                # categorize
                for l in links:
                    s_type = "unknown"
                    if "hglink" in l['href'] or "multi" in l['txt'].lower(): s_type = "multi_hglink"
                    elif "uptobox" in l['href']: s_type = "uptobox"
                    elif "1fichier" in l['href']: s_type = "1fichier"
                    elif "gofile" in l['href']: s_type = "gofile"
                    elif "dood" in l['href']: s_type = "doodstream"
                    
                    if s_type != "unknown":
                        # Check if we already have this type in this batch
                        # We want max 8 cases total, but diverse
                        if len(collected_urls) < 10:
                            entry = {"type": s_type, "url": l['href'], "query": q}
                            # Avoid exact dupes
                            if not any(x['url'] == entry['url'] for x in collected_urls):
                                collected_urls.append(entry)
                                print(f"  + Added {s_type}: {l['href']}")
                                
            except Exception as e:
                print(f"Error scraping {url_to_scrape}: {e}")
            finally:
                context.close()
                
            if len(collected_urls) >= 8: break
            
        browser.close()
        
    with open(URLS_FILE, "w") as f:
        json.dump(collected_urls, f, indent=2)
    print(f"Saved {len(collected_urls)} URLs to {URLS_FILE}")

def test_method_A_download_event(page, url):
    """Method A: Wait for 'download' event (Current Implementation)"""
    print(f"[Method A] Testing: {url}")
    # return success, duration, final_link
    start = time.time()
    try:
        page.goto(url, wait_until="domcontentloaded")
        
        # 1. Handle Interstitials (hglink/multi)
        # Select quality if needed
        # Logic copied/simplified from main
        if "hglink" in url or "multi" in url or "uasopt" in url:
             page.wait_for_timeout(1000) # wait for redirects
             # Try to find quality link
             q_link = page.locator("a").filter(has_text="1080p").first
             if not q_link.is_visible(): q_link = page.locator("a").filter(has_text="720p").first
             if not q_link.is_visible(): q_link = page.locator("a").filter(has_text="quality").first
             
             if q_link.is_visible():
                 print("  > Clicking quality link...")
                 q_link.click()
                 page.wait_for_load_state("domcontentloaded")
        
        # 2. Click Final Download
        dl_btn = page.locator("a.btn-primary:has-text('Download'), button:has-text('Download'), .videoplayer-download").first
        
        if dl_btn.is_visible():
            print("  > Clicking final button & waiting for event...")
            with page.expect_download(timeout=10000) as download_info:
                 dl_btn.click()
            dl = download_info.value
            return True, time.time() - start, dl.url
        else:
            return False, time.time() - start, "No DL button found"
            
    except Exception as e:
        return False, time.time() - start, str(e)

def test_method_B_network_intercept(page, url):
    """Method B: Listen for request to .mp4/.mkv"""
    print(f"[Method B] Testing: {url}")
    start = time.time()
    found_url = [None]
    
    def handle_request(route, request):
        if ".mp4" in request.url or ".mkv" in request.url:
            print(f"  > Intercepted media request: {request.url}")
            found_url[0] = request.url
            route.abort() # Don't actually download
        else:
            route.continue_()

    try:
        page.route("**/*", handle_request)
        page.goto(url, wait_until="domcontentloaded")
        
        # Same navigation logic
        if "hglink" in url or "multi" in url or "uasopt" in url:
             page.wait_for_timeout(1000) 
             q_link = page.locator("a").filter(has_text="1080p").first
             if not q_link.is_visible(): q_link = page.locator("a").filter(has_text="720p").first
             if q_link.is_visible():
                 q_link.click()
                 page.wait_for_load_state("domcontentloaded")
        
        dl_btn = page.locator("a.btn-primary:has-text('Download'), button:has-text('Download'), .videoplayer-download").first
        if dl_btn.is_visible():
            print("  > Clicking final button...")
            dl_btn.click()
            # Wait for request
            page.wait_for_timeout(5000)
            
        if found_url[0]:
            return True, time.time() - start, found_url[0]
        return False, time.time() - start, "No .mp4 request intercepted"

    except Exception as e:
        return False, time.time() - start, str(e)

def test_method_C_popup_check(page, url):
    """Method C: Check for new tabs/popups that contain the file"""
    print(f"[Method C] Testing: {url}")
    start = time.time()
    try:
        page.goto(url, wait_until="domcontentloaded")
        
        # Navigation logic...
        if "hglink" in url or "multi" in url or "uasopt" in url:
             page.wait_for_timeout(1000)
             q_link = page.locator("a").filter(has_text="1080p").first
             if not q_link.is_visible(): q_link = page.locator("a").filter(has_text="720p").first
             if q_link.is_visible(): q_link.click()
             page.wait_for_load_state("domcontentloaded")
             
        dl_btn = page.locator("a.btn-primary:has-text('Download'), button:has-text('Download'), .videoplayer-download").first
        
        if dl_btn.is_visible():
            print("  > Clicking final button & expecting popup...")
            with page.context.expect_page(timeout=5000) as new_page_info:
                dl_btn.click()
            
            new_page = new_page_info.value
            new_page.wait_for_load_state()
            print(f"  > New page: {new_page.url}")
            return True, time.time() - start, new_page.url
        else:
            return False, time.time() - start, "No button"

    except Exception as e:
        return False, time.time() - start, str(e)

def run_suite():
    if not os.path.exists(URLS_FILE):
        gather_test_cases()
    
    with open(URLS_FILE, "r") as f:
        urls = json.load(f)
    
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for case in urls:
            url = case['url']
            ctype = case['type']
            print(f"\n--- Testing Case: {ctype} ({url}) ---")
            
            # Test Method A
            ctxA = browser.new_context()
            pageA = ctxA.new_page()
            successA, timeA, resA = test_method_A_download_event(pageA, url)
            if not successA:
                with open(f"dom_fail_MethodA_{ctype}.html", "w", encoding="utf-8") as f: f.write(pageA.content())
            ctxA.close()
            
            # Test Method B
            ctxB = browser.new_context()
            pageB = ctxB.new_page()
            successB, timeB, resB = test_method_B_network_intercept(pageB, url)
            if not successB:
                with open(f"dom_fail_MethodB_{ctype}.html", "w", encoding="utf-8") as f: f.write(pageB.content())
            ctxB.close()
            
            # Test Method C (Only if A and B failed? Or just compare?)
            # Let's run C anyway
            ctxC = browser.new_context()
            pageC = ctxC.new_page()
            successC, timeC, resC = test_method_C_popup_check(pageC, url)
            ctxC.close()
            
            row = {
                "type": ctype,
                "url": url,
                "MethodA": {"success": successA, "time": timeA, "result": resA},
                "MethodB": {"success": successB, "time": timeB, "result": resB},
                "MethodC": {"success": successC, "time": timeC, "result": resC}
            }
            results.append(row)
            
        browser.close()
    
    # Analyze Results
    print("\n\n=== RESULTS SUMMARY ===")
    winner_counts = {"MethodA": 0, "MethodB": 0, "MethodC": 0, "Fail": 0}
    
    with open(RESULTS_FILE, "w") as f:
        f.write("=== EGYDEAD TEST REPORT ===\n")
        for r in results:
            f.write(f"\nURL: {r['url']} ({r['type']})\n")
            f.write(f"  Method A (Event): {'PASS' if r['MethodA']['success'] else 'FAIL'} - {r['MethodA']['time']:.2f}s - {r['MethodA']['result']}\n")
            f.write(f"  Method B (Net)  : {'PASS' if r['MethodB']['success'] else 'FAIL'} - {r['MethodB']['time']:.2f}s - {r['MethodB']['result']}\n")
            f.write(f"  Method C (Popup): {'PASS' if r['MethodC']['success'] else 'FAIL'} - {r['MethodC']['time']:.2f}s - {r['MethodC']['result']}\n")
            
            if r['MethodA']['success']: winner_counts['MethodA'] += 1
            elif r['MethodB']['success']: winner_counts['MethodB'] += 1
            elif r['MethodC']['success']: winner_counts['MethodC'] += 1
            else: winner_counts['Fail'] += 1
            
        f.write("\n\nTOTALS:\n")
        f.write(json.dumps(winner_counts, indent=2))
        
    print(json.dumps(winner_counts, indent=2))
    print(f"Detailed results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    run_suite()
