import requests
import re
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

# --- CONSTANTS (Directly from CLI v2.0) ---
RGX_SHORTEN_URL = r'https?://[^"]+?/download/[^"]+'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
RGX_QUALITY_TAG = r'tab-content quality.*?a href="(https?://[^"]+?/link/\d+)"'
RGX_SIZE_TAG = r'font-size-14 mr-auto">([0-9.MGB ]+)</'

def get_qualities(url):
    print(f"Fetching Qualities: {url}")
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    page_html = resp.text.replace('\n', '')
    
    parsed_links = re.findall(RGX_QUALITY_TAG, page_html)
    sizes = re.findall(RGX_SIZE_TAG, page_html)
    
    print(f"Found {len(parsed_links)} links and {len(sizes)} sizes")
    
    qualities = {}
    i = 0
    for q in ['1080p', '720p', '480p', '360p', 'Full HD', 'HD', 'SD']:
        if f'>{q}</' in resp.text and i < len(parsed_links):
            size_str = f" ({sizes[i]})" if i < len(sizes) else ""
            qualities[f"{q}{size_str}"] = parsed_links[i]
            i += 1
            
    if not qualities and parsed_links:
        for idx, link in enumerate(parsed_links):
            size_str = f" ({sizes[idx]})" if idx < len(sizes) else ""
            qualities[f"Quality {idx+1}{size_str}"] = link
            
    return qualities

def resolve_link(short_url):
    print(f"Resolving Short URL: {short_url}")
    if not short_url.startswith('http'):
        short_url = 'https://' + short_url
    
    resp = requests.get(short_url, headers=HEADERS)
    match1 = re.search(f'({RGX_SHORTEN_URL})', resp.text)
    
    if match1:
        target = match1.group(1).rstrip('"')
    elif "/download/" in resp.url:
        target = resp.url
    else:
        print("Failed Step 1")
        return None
        
    if not target.startswith('http'): target = 'https://' + target
    print(f"Target Page: {target}")
    
    # Step 2
    resp = requests.get(target, headers=HEADERS)
    if resp.url != target:
        print(f"Redirected to: {resp.url}")
        resp = requests.get(resp.url, headers=HEADERS)
        
    match2 = re.search(RGX_DIRECT_URL, resp.text)
    if match2:
        direct = match2.group(1).rstrip('"')
        final = 'https://' + direct if not direct.startswith('http') else direct
        return final
    
    print("Failed Step 2")
    return None

if __name__ == "__main__":
    test_url = 'https://ak.sv/movie/6094/the-batman-1'
    quals = get_qualities(test_url)
    print(json.dumps(quals, indent=4))
    
    if quals:
        first_q = list(quals.keys())[0]
        print(f"\nTesting resolution for {first_q}...")
        direct = resolve_link(quals[first_q])
        print(f"FINAL DIRECT URL: {direct}")
