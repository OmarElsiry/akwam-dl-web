import traceback
from api.index import _playwright_get_video_url
from curl_cffi import requests

link_id_url = "go.akwam.com.co/link/143994"
try:
    print("Testing Playwright resolution...")
    mp4_url, referer_url, cookie_str = _playwright_get_video_url(link_id_url)
    print("mp4_url:", mp4_url)
    print("referer_url:", referer_url)
    
    if mp4_url:
        headers = {
            'Referer': 'https://akwam.com.co/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Dest': 'video',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site'
        }
        
        print("Making GET request with curl_cffi to downet...")
        resp = requests.get(mp4_url, headers=headers, impersonate="chrome120", stream=True, timeout=15)
        print("Status:", resp.status_code)
        print("Headers:", resp.headers)
        
        if resp.status_code in [200, 206]:
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    print("Successfully streamed chunk of size", len(chunk))
                    break
        else:
            print("Failed. Body:", resp.text)
except Exception as e:
    print("Exception!")
    traceback.print_exc()
