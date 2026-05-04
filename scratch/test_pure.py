import requests
import re

def test_resolve():
    url = "https://go.akwam.com.co/link/177413"
    r1 = requests.get(url)
    html1 = r1.text
    
    dl_links = re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)
    print("Found download links:", dl_links)
    
    if not dl_links: return
    
    for dl_url in dl_links:
        r2 = requests.get(dl_url)
        html2 = r2.text
        
        mp4_matches = re.findall(r'href=["\']([^"\']+\.mp4)["\']', html2)
        if mp4_matches:
            print("FOUND MP4 in", dl_url, ":", mp4_matches[0])
            return

test_resolve()
