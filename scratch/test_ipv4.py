import sys
import socket
from curl_cffi import requests
import re

# Monkeypatch socket.getaddrinfo to force IPv4
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response for response in responses if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

url = "https://go.akwam.com.co/link/143994"

with requests.Session(impersonate="chrome120") as s:
    print("Fetching go.akwam.com.co with IPv4 only...")
    r1 = s.get(url)
    
    dl_links = list(dict.fromkeys(re.findall(r'href="(https?://[^"]+/download/[^"]+)"', r1.text)))
    if not dl_links:
        print("No download link found!")
        sys.exit(1)
        
    download_url = dl_links[0]
    print("Fetching download page:", download_url)
    
    r2 = s.get(download_url, headers={"Referer": url})
    
    # Try to find mp4 link in HTML
    mp4_links = re.findall(r'href="(https?://[^"]+\.mp4[^"]*)"', r2.text)
    if not mp4_links:
        print("No MP4 link found in HTML!")
        sys.exit(1)
        
    video_url = mp4_links[0]
    print("Found MP4 URL:", video_url)
    
    print("\nAttempting to stream with IPv4...")
    r3 = s.get(
        video_url,
        headers={"Referer": download_url},
        stream=True
    )
    
    print("Stream Response Status:", r3.status_code)
    if r3.status_code == 200:
        print("SUCCESS! IP mismatch was the issue!")
        # Print a few bytes to confirm
        print(next(r3.iter_content(100)))
    else:
        print("FAILED!")
        print(r3.text[:200])
