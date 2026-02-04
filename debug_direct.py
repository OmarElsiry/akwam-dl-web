import re
from requests import get

HTTP = 'https://'
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
RGX_QUALITY_TAG = r'tab-content quality.*?a href="(https?://\w*\.*\w+\.\w+/link/\d+)"'
RGX_SIZE_TAG = r'font-size-14 mr-auto">([0-9.MGB ]+)</'

class AkwamAPI:
    def __init__(self, base_url='https://ak.sv/'):
        res = get(base_url)
        self.base_url = res.url.rstrip('/')
        self.search_url = self.base_url + '/search?q='

    def search(self, query, type='movie'):
        query = query.replace(' ', '+')
        url = f'{self.search_url}{query}&section={type}&page=1'
        print(f"Searching: {url}")
        res = get(url)
        content = res.text
        # Finding patterns like https://ak.sv/movie/123/name
        # The script used: rf'({self.url}/{self.type}/\d+/.*?)"'
        pattern = rf'({self.base_url}/{type}/\d+/.*?)"'
        matches = re.findall(pattern, content)
        results = {}
        for match in matches:
            name = match.split('/')[-1].replace('-', ' ').title()
            results[name] = match
        return results

    def fetch_episodes(self, series_url):
        res = get(series_url)
        content = res.text
        pattern = rf'({self.base_url}/episode/\d+/.*?)"'
        matches = re.findall(pattern, content)
        results = {}
        for match in matches:
            name = match.split('/')[-1].replace('-', ' ').title()
            results[name] = match
        return results

    def get_qualities(self, item_url):
        res = get(item_url)
        content = res.text.replace('\n', '')
        qualities_links = re.findall(RGX_DL_URL, content)
        # The script matched qualities manually:
        qualities = {}
        i = 0
        for q in ['1080p', '720p', '480p']:
            if f'>{q}</' in content:
                if i < len(qualities_links):
                    qualities[q] = qualities_links[i]
                    i += 1
        return qualities

    def get_direct_url(self, link_url):
        if not link_url.startswith('http'):
            link_url = HTTP + link_url
        
        # Step 1: Follow link to shortened downloader page
        res = get(link_url)
        shortened_matches = re.findall(RGX_SHORTEN_URL, res.text)
        if not shortened_matches:
            return None
        shortened_url = shortened_matches[0]
        if not shortened_url.startswith('http'):
            shortened_url = HTTP + shortened_url

        # Step 2: Get direct download page
        res = get(shortened_url)
        direct_page_url = res.url
        if direct_page_url != shortened_url:
            res = get(direct_page_url)
        
        direct_matches = re.findall(RGX_DIRECT_URL, res.text)
        if not direct_matches:
            return None
        
        return HTTP + direct_matches[0]

if __name__ == "__main__":
    api = AkwamAPI()
    
    print("--- Searching Movie: Batman ---")
    movies = api.search("batman", "movie")
    for name, url in movies.items():
        if "The Batman" in name:
            print(f"Found: {name} -> {url}")
            quals = api.get_qualities(url)
            print(f"Qualities: {quals}")
            if quals:
                q = [*quals.keys()][0]
                direct = api.get_direct_url(quals[q])
                print(f"Direct ({q}): {direct}")
            break

    print("\n--- Searching Series: Dark ---")
    series = api.search("dark", "series")
    for name, url in series.items():
        print(f"Option: {name} -> {url}")
    
    # Try to find the actual "Dark" series
    target_series = None
    for name, url in series.items():
        if name == "Dark" or "Dark Season" in name:
            target_series = (name, url)
            break
    
    if target_series:
        name, url = target_series
        print(f"\nTarget found: {name} -> {url}")
        episodes = api.fetch_episodes(url)
        print(f"Total Episodes found: {len(episodes)}")
        # Print first few episodes names
        ep_names = list(episodes.keys())
        print(f"Episodes: {ep_names[:5]} ...")
        
        if ep_names:
            ep_name = ep_names[-1] # Usually first episode
            ep_url = episodes[ep_name]
            print(f"Fetching link for: {ep_name}")
            quals = api.get_qualities(ep_url)
            if quals:
                q = [*quals.keys()][0]
                direct = api.get_direct_url(quals[q])
                print(f"Direct Episode ({q}): {direct}")
    else:
        print("\nActual 'Dark' series not found in top results.")
