import re
import requests

RGX_DL_URL = r'https?://\w*\.*\w+\.\w+/link/\d+'
RGX_SHORTEN_URL = r'https?://\w*\.*\w+\.\w+/download/.*?"'
RGX_DIRECT_URL = r'[a-z0-9]{4,}\.\w+\.\w+/download/.*?"'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class AkwamAPI:
    def __init__(self, base_url="https://ak.sv/"):
        resp = requests.get(base_url, headers=HEADERS, timeout=5)
        self.base_url = resp.url.rstrip('/')
        print(f"Base URL: {self.base_url}")

    def search(self, query):
        url = f"{self.base_url}/search?q={query.replace(' ', '+')}&section=movie"
        resp = requests.get(url, headers=HEADERS)
        pattern = rf'({self.base_url}/movie/\d+/.*?)"'
        matches = re.findall(pattern, resp.text)
        return [{'title': m.split('/')[-1], 'url': m} for m in list(dict.fromkeys(matches))]

    def get_qualities(self, url):
        resp = requests.get(url, headers=HEADERS)
        page = resp.text.replace('\n', '')
        pattern = rf'tab-content quality.*?a href="({RGX_DL_URL})"'
        links = re.findall(pattern, page)
        qualities = {}
        i = 0
        for q in ['1080p', '720p', '480p']:
            if f'>{q}</' in resp.text and i < len(links):
                qualities[q] = links[i]
                i += 1
        return qualities

    def resolve_link(self, short_url):
        print(f"1. Shortened: {short_url}")
        resp = requests.get(short_url, headers=HEADERS)
        match = re.search(f'({RGX_SHORTEN_URL})', resp.text)
        if not match: 
            print("Failed at Phase 1")
            return None
        
        target = match.group(1).rstrip('"')
        if not target.startswith('http'): target = 'https://' + target
        print(f"2. Target: {target}")
        
        resp = requests.get(target, headers=HEADERS)
        if resp.url != target:
            resp = requests.get(resp.url, headers=HEADERS)
        
        # print("DEBUG: Page content sample:", resp.text[resp.text.find('download/'):resp.text.find('download/')+200])
        
        # match = re.search(f'({RGX_DIRECT_URL})', resp.text)
        match = re.search(r'href="([^"]*download/[^"]*)"', resp.text)
        if match:
            url = match.group(1)
            return url if url.startswith('http') else 'https://' + url
        
        # Fallback to the original regex but more careful
        match = re.search(f'({RGX_DIRECT_URL})', resp.text)
        if match:
            url = match.group(1).rstrip('"')
            return 'https://' + url
            
        print("Failed at Phase 3")
        return None

api = AkwamAPI()
results = api.search("Batman")
if results:
    q = api.get_qualities(results[0]['url'])
    if q:
        direct = api.resolve_link(q[list(q.keys())[0]])
        print(f"FINAL RESULT: {direct}")
