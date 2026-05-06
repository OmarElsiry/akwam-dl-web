import sys
import time
from curl_cffi import requests
import re

url = "https://go.akwam.com.co/link/143994"

with requests.Session(impersonate="chrome120") as s:
    print("Fetching go.akwam.com.co...")
    r1 = s.get(url)
    
    dl_links = list(dict.fromkeys(re.findall(r'href="(https?://[^"]+/download/[^"]+)"', r1.text)))
    if not dl_links:
        print("No download link found!")
        sys.exit(1)
        
    download_url = dl_links[0]
    print("Fetching download page:", download_url)
    
    r2 = s.get(download_url, headers={"Referer": url})
    
    mp4_links = re.findall(r"(https?://[^\"']+\.mp4[^\"']*)", r2.text)
    if not mp4_links:
        print("No MP4 link found in HTML!")
        sys.exit(1)
        
    video_url = mp4_links[0]
    print("Found MP4 URL:", video_url)
    
    print("\nWaiting 2.5 seconds...")
    time.sleep(2.5)
    
    print("Attempting to stream...")
    # Exact headers a browser sends when clicking <a href="..." download>
    r3 = s.get(
        video_url,
        headers={
            "Referer": download_url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        },
        stream=True
    )
    
    print("Stream Response Status:", r3.status_code)
