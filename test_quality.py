import requests
import re
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

RGX_QUALITY_TAG = r'tab-content quality.*?a href="(https?://\w*\.*\w+\.\w+/link/\d+)"'

def get_qualities(url):
    print(f"Fetching: {url}")
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    
    # Debug: Check if quality tags exist
    print(f"Contains 'tab-content quality': {'tab-content quality' in resp.text}")
    
    page_content = resp.text.replace('\n', '')
    parsed_links = re.findall(RGX_QUALITY_TAG, page_content)
    print(f"Links found by regex: {len(parsed_links)}")
    
    qualities = {}
    i = 0
    # Try multiple common patterns if the primary fails
    for q in ['1080p', '720p', '480p', '360p', 'Full HD', 'HD', 'SD']:
        if f'>{q}</' in resp.text and i < len(parsed_links):
            qualities[q] = parsed_links[i]
            i += 1
            
    # If standard logic fails, just pair whatever links we found with labels
    if not qualities and parsed_links:
        for idx, link in enumerate(parsed_links):
            qualities[f"Quality {idx+1}"] = link
            
    return qualities

RGX_SHORTEN_URL = r'https?://\w*\.*\w+\.\w+/download/.*?"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'

def resolve_link(short_url):
    print(f"Resolving: {short_url}")
    resp = requests.get(short_url, headers=HEADERS)
    print(f"Short URL response status: {resp.status_code}")
    
    match1 = re.search(f'({RGX_SHORTEN_URL})', resp.text)
    if not match1:
        print("Failed to find download page link (match1)")
        # Maybe it's a direct redirect?
        if "download" in resp.url:
            print(f"Redirected directly to: {resp.url}")
            target = resp.url
        else:
            return None
    else:
        target = match1.group(1).rstrip('"')
        print(f"Found download page: {target}")

    if not target.startswith('http'): target = 'https://' + target
    
    # Step 2: Download Page -> Final Direct Link
    resp = requests.get(target, headers=HEADERS)
    print(f"Download page response status: {resp.status_code}")
    
    match2 = re.search(f'({RGX_DIRECT_URL})', resp.text)
    if match2:
        final_url = match2.group(1).rstrip('"')
        print(f"Found direct link: {final_url}")
        return final_url if final_url.startswith('http') else 'https://' + final_url
    
    print("Failed to find direct link (match2)")
    return None

if __name__ == "__main__":
    test_url = 'https://ak.sv/episode/4089/plan-pars-%D8%A7%D9%84%D8%A7%D8%AE%D9%8A%D8%B1%D8%A9'
    res = get_qualities(test_url)
    print(json.dumps(res, indent=4))
    
    if "720p" in res:
        direct = resolve_link(res["720p"])
        print(f"FINAL DIRECT URL: {direct}")
