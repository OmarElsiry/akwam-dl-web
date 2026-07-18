import re
import sys
sys.path.insert(0, '.')
from api.akwam_api import safe_get, HTTP

RGX_SHORTEN_URL = r'https?://([\w.-]+/download/.*?)"'
RGX_DIRECT_URL = r'([\w.-]+/download/.*?)"'

def resolve_direct_url(link_id_url):
    url = HTTP + link_id_url
    r1 = safe_get(url)
    
    m1 = re.search(RGX_SHORTEN_URL, r1.content.decode())
    if not m1:
        print("Failed to find SHORTEN_URL in", r1.url)
        return None
    
    short_url = HTTP + m1.group(1)
    
    r2 = safe_get(short_url)
    final_html = r2.content.decode()
    if short_url != r2.url:
        r2 = safe_get(r2.url)
        final_html = r2.content.decode()

    m2 = re.search(RGX_DIRECT_URL, final_html)
    if not m2:
        print("Failed to find DIRECT_URL in", r2.url)
        return None
        
    return HTTP + m2.group(1)

print("Resolved URL:", resolve_direct_url('go.akwam.com.co/link/153885'))
