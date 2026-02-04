from requests import get
import re

HTTP = 'https://'
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'

def get_direct_url(link_url):
    if not link_url.startswith('http'): link_url = HTTP + link_url
    res = get(link_url)
    shortened = re.findall(RGX_SHORTEN_URL, res.text)
    if not shortened: return None
    s_url = shortened[0]
    if not s_url.startswith('http'): s_url = HTTP + s_url
    res = get(s_url)
    if res.url != s_url: res = get(res.url)
    direct = re.findall(RGX_DIRECT_URL, res.text)
    return HTTP + direct[0] if direct else None

def fetch_all_dark():
    base_url = get('https://ak.sv/').url.rstrip('/')
    # Search for Dark Season 1
    search_url = f"{base_url}/search?q=dark+season+1&section=series"
    res = get(search_url)
    # Target: https://ak.sv/series/477/dark-الموسم-الاول
    series_match = re.search(rf'({base_url}/series/\d+/.*?-Ø§ÙØ¯ÙØ³Ù-Ø§ÙØ§ÙÙ)"', res.text)
    if not series_match:
        # Try generic match
        series_match = re.search(rf'({base_url}/series/\d+/dark.*?)"', res.text)
    
    if not series_match:
        print("Could not find Dark Season 1")
        return

    series_url = series_match.group(1)
    print(f"Found Series: {series_url}")
    
    # Get episodes
    res = get(series_url)
    episodes = re.findall(rf'({base_url}/episode/\d+/.*?)"', res.text)
    print(f"Found {len(episodes)} episodes")
    
    for ep_url in episodes[:3]: # Just first 3 for brevity in verification
        name = ep_url.split('/')[-1]
        print(f"Fetching {name}...")
        res = get(ep_url)
        content = res.text.replace('\n', '')
        links = re.findall(RGX_DL_URL, content)
        if links:
            direct = get_direct_url(links[0])
            print(f"  Direct: {direct}")

if __name__ == "__main__":
    fetch_all_dark()
