import os
import sys
import time
import re
import requests
import argparse
from urllib.parse import unquote
from egydead_dl import EgyDeadDL
from playwright.sync_api import sync_playwright

# Force UTF-8 output/input for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')

def resolve_multi_download(url, quality_preference=None):
    """
    Resolves a 'Multi Download' or file host link to get the final direct download URL.
    Handles redirects (hglink->uasopt->uptobox), overlays, timers (1fichier), and network interception.
    Returns: (final_url, quality_name)
    """
    print(f"Resolving URL: {url}")
    final_url = None
    selected_quality = "Unknown"
    
    with sync_playwright() as p:
        # Use HEADED mode for better ReCAPTCHA success
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True,
            accept_downloads=True
        )
        
        # 1. Aggressive Overlay \ Ad Killer
        context.add_init_script("""
            setInterval(() => {
                // Remove invisible full-screen overlays
                document.querySelectorAll('div[style*="z-index"][style*="2147483647"]').forEach(e => e.remove());
                document.querySelectorAll('div[style*="fixed"][style*="inset:0px"]').forEach(e => e.remove());
                // Remove specific ad IFrames if known
                document.querySelectorAll('iframe[src*="googleads"], iframe[src*="doubleclick"]').forEach(e => e.remove());
            }, 500);
        """)

        page = context.new_page()
        
        # 2. Network Sniffer for Media Fallback
        media_candidates = []
        def on_request(request):
            if request.resource_type in ["media", "fetch", "xhr"]:
                if any(ext in request.url for ext in [".mp4", ".mkv", ".avi", "manifest.mpd", ".m3u8"]):
                    if ".ts" not in request.url and "google" not in request.url:
                        media_candidates.append(request.url)
        page.on("request", on_request)

        try:
            print("Navigating...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # Resolution Loop (Handle redirects/intermediates)
            max_redirects = 8
            for _ in range(max_redirects):
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(1000) # Settle
                
                curr_url = page.url
                print(f"Current Page: {curr_url}")

                # --- Exit Conditions ---
                if "alliance4creativity" in curr_url or "Account Suspended" in page.title():
                    print("Link is dead/seized.")
                    return None, None
                
                # Check for direct media URL
                if any(curr_url.endswith(x) for x in [".mp4", ".mkv", ".avi"]):
                    final_url = curr_url
                    selected_quality = "DirectURL"
                    break

                # --- HOST HANDLERS ---

                # 1. 1fichier
                if "1fichier" in curr_url:
                    print("Detected 1fichier.")
                    try:
                        dl_btn = page.locator("#dlw, input[type='submit'][value='Download'], .btn-orange").first
                        if dl_btn.is_visible():
                            # WAIT LOOP for timer
                            print("Checking 1fichier timer...")
                            for _ in range(120): # Wait up to 120s
                                txt = dl_btn.inner_text() or dl_btn.get_attribute("value") or ""
                                is_disabled = dl_btn.is_disabled()
                                if not is_disabled and "wait" not in txt.lower() and "download in" not in txt.lower():
                                    break
                                page.wait_for_timeout(1000)
                            
                            print("Clicking 1fichier download...")
                            try:
                                with page.expect_download(timeout=10000) as download_info:
                                    dl_btn.click()
                                final_url = download_info.value.url
                                selected_quality = "Original"
                                break
                            except:
                                print("Download event missed or redirected. Checking page content...")
                                # Fallback handled below
                        
                        # Fallback / Redirect Check
                        page.wait_for_load_state("domcontentloaded")
                        link = page.locator("a:has-text('Click here to download')").first
                        if link.is_visible():
                            print("Found direct 'Click here' link.")
                            final_url = link.get_attribute("href")
                            selected_quality = "Original"
                            break

                    except Exception as e:
                        print(f"1fichier error: {e}")
                    break

                # 2. UptoBox
                elif "uptobox" in curr_url:
                     print("Detected UptoBox.")
                     try:
                         # 2a. Free Download Button (First Page)
                         btn = page.locator("input[value='Free Download'], button:has-text('Free Download')").first
                         if btn.is_visible():
                             print("Clicking 'Free Download'...")
                             btn.click()
                             continue

                         # 2b. Wait Page / Download Link
                         wait_link = page.locator("a#btn_download").first
                         if wait_link.is_visible():
                             print("Waiting for UptoBox timer/button...")
                             for _ in range(70): 
                                 if wait_link.is_visible():
                                     cls = wait_link.get_attribute("class") or ""
                                     if "disabled" not in cls:
                                         break
                                 page.wait_for_timeout(1000)
                             
                             print("Clicking UptoBox download link...")
                             with page.expect_download(timeout=20000) as dl_info:
                                 wait_link.click()
                             final_url = dl_info.value.url
                             selected_quality = "Original"
                             break
                     except Exception as e:
                         print(f"UptoBox error: {e}")
                         break

                # 3. GoFile
                elif "gofile" in curr_url:
                    print("Detected GoFile.")
                    try:
                        page.wait_for_selector("#filesContent", timeout=15000)
                        dl_link = page.locator("a.download-button, a[href*='gofile.io/download']").first
                        if dl_link.is_visible():
                            final_url = dl_link.get_attribute("href")
                            selected_quality = "Original"
                            break
                    except: pass
                    break

                # 4. HgLink / Generic Intermediates
                else:
                    print("Scanning for intermediate download buttons...")
                    
                    # Broad selectors for final step of these generated sites
                    selectors = [
                        ".videoplayer-download",
                        "a:has-text('Download')",
                        "#download-btn",
                        ".btn-download",
                        "a[class*='btn'][class*='download']",
                        "button[class*='btn'][class*='download']",
                        ".g-recaptcha",
                        ".submit-btn",
                        "input[type='submit']"
                    ]
                    
                    btn = page.locator(",".join(selectors)).first
                    
                    if btn.is_visible():
                        print("Clicking intermediate button...")
                        old_url = page.url
                        
                        try:
                            # Handling Popups vs Nav
                            with context.expect_page(timeout=3000) as new_page_info:
                                btn.click()
                            
                            new_page = new_page_info.value
                            new_page.wait_for_load_state("domcontentloaded")
                            new_page_url = new_page.url
                            print(f"Popup opened: {new_page_url}")

                            bad_domains = ["grabtrust", "ad", "popup", "revenue", "bet", "casino"]
                            if any(b in new_page_url for b in bad_domains):
                                print("Detected Ad popup. Closing.")
                                new_page.close()
                                
                                page.wait_for_timeout(1000)
                                if page.url != old_url:
                                    print("Main page navigated while popup opened.")
                                    continue
                                else:
                                    print("Ad closed, but no navigation. Retrying click or scanning...")
                                    continue
                            else:
                                print("Switching to new tab (likely host).")
                                page.close()
                                page = new_page
                                page.bring_to_front()
                                continue

                        except:
                            # No popup
                            # Wait longer for potential form submit / redirect
                            page.wait_for_timeout(6000)
                            if page.url != old_url:
                                print(f"Navigated in-page to {page.url}")
                                continue
                            else:
                                print("Click had no effect. Retrying...")
                                try:
                                    btn.evaluate("e => e.click()")
                                except: pass
                                
                                page.wait_for_timeout(4000)
                                if page.url != old_url: continue
                                break
                    else:
                        print("No recognizable button found.")
                        link = page.locator("a:has-text('Click here')").first
                        if link.is_visible():
                             print("Found text link, trying...")
                             link.click()
                             continue
                        break

            # --- Final Fallback ---
            if not final_url and media_candidates:
                print(f"Using network sniffed media ({len(media_candidates)} found).")
                final_url = media_candidates[-1]
                selected_quality = "NetworkIntercept"

        except Exception as e:
            print(f"Resolution crashed: {e}")
        
        browser.close()
    
    if final_url:
        print(f"-> Resolved: {final_url}")
    else:
        print("-> Failed to resolve direct link.")
        
    return final_url, selected_quality

def download_file(url, folder, filename):
    try:
        print(f"Downloading: {filename}")
        print(f"URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://haxloppd.com/'
        }
        
        with requests.get(url, stream=True, headers=headers, timeout=30) as r:
            r.raise_for_status()
            
            filepath = os.path.join(folder, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print("Download complete.")
            return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def process_download_item(dl, url, title, download_folder, action):
    print(f"Processing: {title}...")
    
    server_to_resolve = None
    link_list_debug = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 1. Navigate to Episode Page
            print("Navigating to episode page...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # 2. Click "Watch and Download" to reveal servers
            try:
                # Fix selector syntax: Use proper OR logic or separate checks
                btn1 = page.locator(".watchNow button")
                btn2 = page.locator("text='المشاهده والتحميل'")
                watch_button = btn1.or_(btn2).first
                
                if watch_button.is_visible():
                    print("Clicking 'Watch and Download' button...")
                    watch_button.click()
                    page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Warning: Could not click watch button: {e}")

            # 3. Scrape Server Links
            print("Scanning for download servers...")
            try:
                page.wait_for_selector(".downloadv-item, .ser-link, a:has-text('تحميل')", timeout=5000)
            except:
                print("No specific server list selector found immediately, parsing all links...")

            link_data = page.evaluate("""() => {
                const links = [];
                const items = document.querySelectorAll('.downloadv-item, .ser-link, li.download-item a');
                
                items.forEach(a => {
                    const href = a.href;
                    if (!href || href.includes('javascript')) return;
                    
                    let name = a.innerText.trim();
                    if (!name) name = a.querySelector('.name, .ser-name, span')?.innerText || "Unknown";
                    name = name.replace(/\\n/g, ' ').replace(/\\s+/g, ' ').trim();
                    
                    links.push({
                        'server': name,
                        'url': href,
                        'quality': "Unknown"
                    });
                });
                
                if (links.length === 0) {
                     document.querySelectorAll('a').forEach(a => {
                        const href = a.href;
                        const text = a.innerText;
                        if (href && (href.includes('hglink') || href.includes('uptobox') || href.includes('1fichier') || href.includes('gofile') || text.includes('تحميل متعدد'))) {
                             links.push({ 'server': text || 'Unknown', 'url': href, 'quality': 'Unknown' });
                        }
                     });
                }
                return links;
            }""")
            
            # Filter and dedup
            link_list = []
            seen_urls = set()
            for l in link_data:
                q = "Unknown"
                name_lower = l['server'].lower()
                if "1080" in name_lower: q = "1080p"
                elif "720" in name_lower: q = "720p"
                elif "480" in name_lower: q = "480p"
                l['quality'] = q
                
                if l['url'] not in seen_urls:
                    seen_urls.add(l['url'])
                    link_list.append(l)
            
            link_list_debug = link_list

            if not link_list:
                print("No download links found on the page.")
                with open("debug_playwright_source.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
            else:
                print(f"Found {len(link_list)} download servers.")

                # Prioritize servers
                multi_server = None
                for link in link_list:
                    s_name = link['server'].lower()
                    u_link = link['url']
                    if "تحميل متعدد" in s_name or "multi" in s_name or "hglink" in u_link or "dumbalag" in u_link:
                        multi_server = link
                        break
                
                if multi_server:
                    print(f"Found 'Multi Download' server: {multi_server['url']}")
                    server_to_resolve = multi_server['url']
                else:
                    print("No 'Multi Download' server found. Checking alternatives...")
                    # Attempt others
                    for link in link_list:
                        s_name = link['server'].lower()
                        u_link = link['url']
                        if "uptobox" in s_name or "uptobox" in u_link:
                            print(f"Trying UptoBox: {u_link}")
                            server_to_resolve = u_link
                            break
                        if "1fichier" in s_name or "1fichier" in u_link:
                            print(f"Trying 1fichier: {u_link}")
                            server_to_resolve = u_link
                            break
                        if "gofile" in s_name or "gofile" in u_link:
                            print(f"Trying GoFile: {u_link}")
                            server_to_resolve = u_link
                            break

        except Exception as e:
            print(f"Error scraping item: {e}")
        finally:
            browser.close()
    
    # 4. Resolve Link (Outside nested context)
    if server_to_resolve:
        try:
            final_url, quality_name = resolve_multi_download(server_to_resolve)
            
            # Handle Result
            if final_url:
                if not quality_name: quality_name = "Unknown_Quality"
                print(f"SUCCESS: Final Direct Link: {final_url}")
                
                if action == "download":
                    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in ' .-_']).strip()
                    ext = ".mp4"
                    if "mkv" in final_url: ext = ".mkv"
                    filename = f"{safe_title}_{quality_name}{ext}"
                    download_file(final_url, download_folder, filename)
                else:
                    print("-" * 30)
                    print(f"Link ({quality_name}): {final_url}")
                    print("-" * 30)
            else:
                print("Failed to resolve a direct download link.")
        except Exception as e:
            print(f"Error resolving link: {e}")
            
    elif link_list_debug:
         print("Failed to find a supported server to resolve automatically.")
         print("Available Servers:")
         for i, l in enumerate(link_list_debug):
             print(f"{i+1}. {l['server']} - {l['url']}")

def print_header():
    print("\n" + "="*50)
    print("           EGYDEAD DOWNLOADER CLI           ")
    print("="*50 + "\n")

def print_separator():
    print("-" * 50)

def main():
    print_header()
    
    parser = argparse.ArgumentParser(description="EgyDead Downloader")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--mode", choices=["movie", "series"], help="Content type")
    parser.add_argument("--action", choices=["download", "link"], help="Action to perform")
    args = parser.parse_args()

    # 1. Get Mode
    mode = None
    while not mode:
        if args.mode:
            mode = args.mode
        else:
            print("Select Mode:")
            print(" [1] Movie")
            print(" [2] Series")
            print(" [0] Exit")
            choice = input("Selection: ").strip()
            if choice == '1':
                mode = "movie"
            elif choice == '2':
                mode = "series"
            elif choice == '0':
                sys.exit(0)
            else:
                print("Invalid selection.")
    
    print_separator()

    # 2. Get Action
    action = None
    while not action:
        if args.action:
            action = args.action
        else:
            print("Select Action:")
            print(" [1] Download File")
            print(" [2] Get Direct Link Only")
            print(" [0] Back")
            choice = input("Selection: ").strip()
            if choice == '1':
                action = "download"
            elif choice == '2':
                action = "link"
            elif choice == '0':
                mode = None # Loop back
                main()
                return
            else:
                print("Invalid selection.")

    print_separator()

    # 3. Get Query
    if args.query:
        query = args.query
    else:
        query = input("Enter search query: ").strip()
        if not query:
            print("Query cannot be empty.")
            return

    dl = EgyDeadDL()
    print(f"\nSearching for '{query}'...")
    results = dl.search(query)
    
    if not results:
        print("No results found. Please try a different query.")
        return

    # 4. Select Content
    print("\nSelect Content:")
    for i, res in enumerate(results):
        print(f" [{i+1}] {res['title']}")
    
    selected_page = None
    while True:
        try:
            val = input(f"Selection (1-{len(results)}): ").strip()
            choice = int(val) - 1
            if 0 <= choice < len(results):
                selected_page = results[choice]
                break
        except ValueError:
            pass
        print("Invalid selection.")

    print(f"\nSelected: {selected_page['title']}")
    print_separator()
    
    download_folder = os.path.join("downloaded", query.replace(" ", "_"))
    if action == "download":
        os.makedirs(download_folder, exist_ok=True)

    # 5. Process based on Mode
    if mode == "movie":
        print("Fetching content details...")
        resp = requests.get(selected_page['url'], headers=dl.headers)
        
        # Check if it's a collection
        sub_links = re.findall(r'<li class="movieItem">\s*<a href="([^"]+)" title="([^"]+)"', resp.text)
        
        if not sub_links:
             sub_links = re.findall(r'<a href="([^"]+)"[^>]*class="[^"]*BlockItem[^"]*"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

        cleaned_sub_items = []
        for link, title_or_html in sub_links:
             if "<" in title_or_html:
                 title_match = re.search(r'alt="([^"]+)"', title_or_html)
                 title = title_match.group(1) if title_match else "Unknown Title"
             else:
                 title = title_or_html

             if "Episode" not in link and "/episode/" not in link:
                 cleaned_sub_items.append({'url': link, 'title': title})

        if cleaned_sub_items:
            print(f"\nFound {len(cleaned_sub_items)} items in this collection:")
            for i, item in enumerate(cleaned_sub_items):
                print(f" [{i+1}] {item['title']}")
            
            print("\nSelect item to download (enter 0 for all):")
            while True:
                try:
                    val = input(f"Selection (0-{len(cleaned_sub_items)}): ").strip()
                    choice = int(val)
                    if choice == 0:
                        for item in cleaned_sub_items:
                             process_download_item(dl, item['url'], item['title'], download_folder, action)
                        break
                    elif 0 < choice <= len(cleaned_sub_items):
                        item = cleaned_sub_items[choice-1]
                        process_download_item(dl, item['url'], item['title'], download_folder, action)
                        break
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input.")
        else:
            process_download_item(dl, selected_page['url'], selected_page['title'], download_folder, action)
    
    elif mode == "series":
        print("Fetching episodes...")
        resp = requests.get(selected_page['url'], headers=dl.headers)
        
        episode_links = re.findall(r'href="([^"]*/episode/[^"]+)"', resp.text)
        # Filter social links and ensure uniqueness
        filtered_links = []
        seen_links = set()
        for link in episode_links:
            if link.endswith("/episode/"):
                continue
            if any(x in link.lower() for x in ['facebook', 'twitter', 'whatsapp', 'telegram', 'pinterest', 'reddit']):
                continue
            if link not in seen_links:
                seen_links.add(link)
                filtered_links.append(link)
        
        episode_links = filtered_links
        
        def get_ep_num(url):
            # Try english 'episode-X'
            match = re.search(r'episode-(\d+)', url)
            if match:
                return int(match.group(1))
            # Try arabic 'الحلقة-X'
            match = re.search(r'(?:episode|الحلقة)[-_](\d+)', unquote(url))
            return int(match.group(1)) if match else 0
        
        episode_links.sort(key=get_ep_num)
        
        if not episode_links:
            print("No episodes found.")
            return

        print(f"Found {len(episode_links)} episodes.")

        print("Enter episode number(s) (e.g. '1', '1-5', 'all'):")
        
        selected_indices = []
        while True:
            ep_input = input("> ").strip()
            if ep_input.lower() == 'all':
                selected_indices = range(len(episode_links))
                break
            elif '-' in ep_input:
                try:
                    start, end = map(int, ep_input.split('-'))
                    selected_indices = range(start-1, end)
                    break
                except ValueError:
                    print("Invalid range format.")
            else:
                try:
                    val = int(ep_input)
                    if 1 <= val <= len(episode_links):
                        selected_indices = [val - 1]
                        break
                    else:
                        print(f"Invalid number. Please enter 1-{len(episode_links)}.")
                except ValueError:
                    print("Invalid input.")

        for idx in selected_indices:
            if idx < 0 or idx >= len(episode_links):
                continue
                
            ep_url = episode_links[idx]
            ep_num = get_ep_num(ep_url)
            if ep_num == 0:
                ep_num = idx + 1
                
            item_name = f"{selected_page['title']}_Ep{ep_num}"
            process_download_item(dl, ep_url, item_name, download_folder, action)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
