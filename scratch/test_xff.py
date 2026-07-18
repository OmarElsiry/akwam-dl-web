import sys
from curl_cffi import requests
import re

url = "https://go.akwam.com.co/link/143994"
fake_ip = "8.8.8.8"

with requests.Session(impersonate="chrome120") as s:
    print(f"Fetching go.akwam.com.co with X-Forwarded-For: {fake_ip}...")
    headers = {"X-Forwarded-For": fake_ip}
    r1 = s.get(url, headers=headers)
    
    dl_links = list(dict.fromkeys(re.findall(r'href="(https?://[^"]+/download/[^"]+)"', r1.text)))
    if not dl_links:
        print("No download link found!")
        print("Response:", r1.status_code)
        print("Text:", r1.text[:500])
        sys.exit(1)
        
    download_url = dl_links[0]
    print("Fetching download page:", download_url)
    
    headers["Referer"] = url
    r2 = s.get(download_url, headers=headers)
    
    # Try to find mp4 link in HTML
    mp4_links = re.findall(r'href="(https?://[^"]+\.mp4[^"]*)"', r2.text)
    if not mp4_links:
        print("No MP4 link found in HTML!")
        sys.exit(1)
        
    video_url = mp4_links[0]
    print("Found MP4 URL:", video_url)
    
    print("\nAttempting to stream...")
    # Attempt to stream using the fake IP. Since we don't control 8.8.8.8, the request will come from our IP.
    # If the token is bound to 8.8.8.8, this request WILL FAIL (403).
    r3 = s.get(
        video_url,
        headers={"Referer": download_url},
        stream=True
    )
    
    print("Stream Response Status (from real IP):", r3.status_code)

