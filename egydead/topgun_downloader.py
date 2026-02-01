import os
import requests
import re
from urllib.parse import unquote
from egydead_dl import EgyDeadDL
import time

def download_file(url, folder, filename_prefix="file", headers=None):
    try:
        print(f"Attempting to download from: {url}")
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        
        with requests.get(url, stream=True, allow_redirects=True, timeout=30, headers=headers) as r:
            r.raise_for_status()
            
            # Check content type
            content_type = r.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            
            if 'text/html' in content_type:
                print("Link returned HTML page, not a file.")
                # Debug HTML
                try:
                    title = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE)
                    title_text = title.group(1) if title else "No Title"
                    print(f"Page Title: {title_text}")
                    print(f"Snippet: {r.text[:200]}...")
                except:
                    pass
                return False, f"Returned HTML page: {title_text}"

            # Try to get filename from headers
            filename = None
            if "Content-Disposition" in r.headers:
                cd = r.headers["Content-Disposition"]
                fname_match = re.search(r'filename="?([^"]+)"?', cd)
                if fname_match:
                    filename = fname_match.group(1)
            
            if not filename:
                # Guess from URL
                filename = unquote(url.split('/')[-1])
                if not filename or len(filename) > 100:
                    filename = f"{filename_prefix}_{int(time.time())}.mp4" # Default extension
            
            # Sanitize filename
            filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in "._- "]).strip()
            filepath = os.path.join(folder, filename)
            
            print(f"Downloading to: {filepath}")
            
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            print("Download complete.")
            return True, filepath
            
    except Exception as e:
        print(f"Download failed: {e}")
        return False, str(e)

def main():
    dl = EgyDeadDL()
    search_query = "Top Gun"
    print(f"Searching for '{search_query}'...")
    results = dl.search(search_query)
    
    target_movie = None
    for res in results:
        if "1986" in res['title'] or "Top Gun 1" in res['title']:
            target_movie = res
            break
    
    if not target_movie:
        print("Could not find 'Top Gun 1' or '1986' version.")
        if results:
            target_movie = results[0]
            print(f"Falling back to first result: {target_movie['title']}")
        else:
            return

    print(f"Selected: {target_movie['title']}")
    
    # Create directory
    safe_title = "".join([c for c in target_movie['title'] if c.isalpha() or c.isdigit() or c in "._- "]).strip()
    download_dir = os.path.join("downloaded", safe_title)
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"Fetching download links for: {target_movie['url']}")
    links = dl.get_download_links(target_movie['url'])
    
    if not links:
        print("No download links found.")
        return

    report = []
    
    for i, link in enumerate(links):
        server = link['server']
        original_url = link['url']
        quality = link['quality']
        
        print(f"\n--- Processing Link {i+1}/{len(links)}: {server} ({quality}) ---")
        
        direct_url = None
        download_headers = dl.headers.copy()
        
        # Try to resolve if it's DoodStream
        if 'dood' in original_url or 'dsvplay' in original_url:
            print("Resolving DoodStream...")
            direct_url = dl.resolve_doodstream(original_url)
            # Important: DoodStream often requires the Referer to be the embed page
            download_headers['Referer'] = original_url
        else:
            direct_url = original_url

        if direct_url:
            success, msg = download_file(direct_url, download_dir, filename_prefix=f"video_{i}", headers=download_headers)
            if success:
                report.append(f"SUCCESS: {server} ({quality}) - Saved to {msg}")
            else:
                report.append(f"FAILED: {server} ({quality}) - {msg}")
        else:
            report.append(f"FAILED: {server} ({quality}) - Could not resolve direct link")

    print("\n\n=== DOWNLOAD REPORT ===")
    for line in report:
        print(line)
    
    # Save report to file
    with open(os.path.join(download_dir, "report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    main()
