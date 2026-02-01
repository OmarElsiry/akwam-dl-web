import re
import requests
import sys

# Set default encoding to utf-8 for stdout
sys.stdout.reconfigure(encoding='utf-8')

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
        print(f"[INIT] Base URL: {self.base_url}")

    def search(self, query, _type='movie'):
        url = f"{self.base_url}/search?q={query.replace(' ', '+')}&section={_type}"
        print(f"[SEARCH] ({_type}) Query: {query}")
        resp = requests.get(url, headers=HEADERS)
        pattern = rf'({self.base_url}/{_type}/\d+/.*?)"'
        matches = list(dict.fromkeys(re.findall(pattern, resp.text)))
        return [{'title': m.split('/')[-1], 'url': m} for m in matches]

    def fetch_episodes(self, series_url):
        print(f"[EPISODES] Fetching from: {series_url}")
        resp = requests.get(series_url, headers=HEADERS)
        pattern = rf'({self.base_url}/episode/\d+/.*?)"'
        matches = list(dict.fromkeys(re.findall(pattern, resp.text)))
        return [{'title': m.split('/')[-1], 'url': m} for m in matches[::-1]]

    def get_qualities(self, url):
        print(f"[QUALITIES] Fetching for: {url}")
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
        print(f"[RESOLVE] Step 1 (Short): {short_url}")
        resp = requests.get(short_url, headers=HEADERS)
        match = re.search(f'({RGX_SHORTEN_URL})', resp.text)
        if not match: return None
        
        target = match.group(1).rstrip('"')
        if not target.startswith('http'): target = 'https://' + target
        print(f"[RESOLVE] Step 2 (Target): {target}")
        
        resp = requests.get(target, headers=HEADERS)
        if resp.url != target:
            resp = requests.get(resp.url, headers=HEADERS)
        
        match = re.search(f'({RGX_DIRECT_URL})', resp.text)
        if match:
            url = match.group(1).rstrip('"')
            return url if url.startswith('http') else 'https://' + url
        return None

def test_everything():
    api = AkwamAPI()
    
    # 1. MOVIE TEST
    print("\n--- MOVIE TEST ---")
    movie_results = api.search("Batman", "movie")
    if movie_results:
        movie = movie_results[0]
        print(f"Selected Movie: {movie['title']}")
        qualities = api.get_qualities(movie['url'])
        if qualities:
            q = list(qualities.keys())[0]
            direct = api.resolve_link(qualities[q])
            print(f"RESULT: {direct}")
    
    # 2. SERIES TEST
    print("\n--- SERIES TEST ---")
    # Using a common series name
    series_results = api.search("Suits", "series")
    if series_results:
        series = series_results[0]
        print(f"Selected Series: {series['title']}")
        episodes = api.fetch_episodes(series['url'])
        if episodes:
            episode = episodes[0] 
            print(f"Selected Episode: {episode['title']}")
            qualities = api.get_qualities(episode['url'])
            if qualities:
                q = list(qualities.keys())[0]
                direct = api.resolve_link(qualities[q])
                print(f"RESULT: {direct}")

if __name__ == "__main__":
    test_everything()
