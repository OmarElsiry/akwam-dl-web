"""
Non-interactive test script to understand Akwam-DL workflow
"""
import re, os, sys
from requests import get

HTTP = 'https://'
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
RGX_QUALITY_TAG = rf'tab-content quality.*?a href="{RGX_DL_URL}"'
RGX_SIZE_TAG = r'font-size-14 mr-auto">([0-9.MGB ]+)</'

class Akwam:
    def __init__(self, url):
        url = get(url).url
        self.url = [url, url[:-1]][url[-1] == '/']
        self.search_url = self.url + '/search?q='
        self.cur_page = None
        self.qualities = {}
        self.results = None
        self.parsed = None
        self.dl_url = None
        self.type = 'movie'

    def select(self, choice, is_index=False):
        if is_index:
            choice = [*self.results.keys()][choice - 1]
        self.cur_url = self.results[choice]

    def parse(self, regex, no_multi_line=False):
        page = self.cur_page.content.decode()
        if no_multi_line:
            page = page.replace('\n', '')
        self.parsed = re.findall(regex, page)

    def load(self):
        self.cur_page = get(self.cur_url)
        self.parse(RGX_QUALITY_TAG, no_multi_line=True)
        i = 0
        for q in ['1080p', '720p', '480p']:
            if f'>{q}</' in self.cur_page.text:
                self.qualities[q] = self.parsed[i]
                i += 1
        self.parse(RGX_SIZE_TAG, no_multi_line=True)

    def search(self, query, page=1):
        query = query.replace(' ', '+')
        self.cur_page = get(f'{self.search_url}{query}&section={self.type}&page={page}')
        self.parse(rf'({self.url}/{self.type}/\d+/.*?)"')
        self.results = {
            url.split('/')[-1].replace('-', ' ').title(): url \
                for url in self.parsed[::-1]
        }

    def fetch_episodes(self):
        self.cur_page = get(self.cur_url)
        self.parse(rf'({self.url}/episode/\d+/.*?)"')
        self.results = {
            url.split('/')[-1].replace('-', ' ').title(): url \
                for url in self.parsed[::-1]
        }

    def get_direct_url(self, quality='720p'):
        print('>> Solving shortened URL...')
        self.cur_page = get(HTTP + self.qualities[quality])
        self.parse(RGX_SHORTEN_URL)

        print('>> Getting Direct URL...')
        self.cur_page = get(HTTP + self.parsed[0])

        if HTTP + self.parsed[0] != self.cur_page.url:
            print('>> Fix non-direct URL...')
            self.cur_page = get(self.cur_page.url)

        self.parse(RGX_DIRECT_URL)
        self.dl_url = HTTP + self.parsed[0]

    def recursive_episodes(self):
        series_episodes = []
        for name, url in self.results.items():
            try:
                print(f'\n>>> Getting episode {name}...')
                self.cur_url = url
                self.load()
                quality = [*self.qualities][0]
                self.get_direct_url(quality)
                series_episodes.append(self.dl_url)
            except Exception as e:
                print('>> Error Caught ->', e)
        return series_episodes


def test_movie():
    print("\n" + "="*60)
    print("TESTING MOVIE MODE: Searching for 'batman'")
    print("="*60)
    
    API = Akwam('https://ak.sv/')
    print(f"Resolved base URL: {API.url}")
    
    API.type = 'movie'
    API.search('batman')
    
    print(f"\nFound {len(API.results)} results:")
    for n, (name, url) in enumerate(list(API.results.items())[:5]):
        print(f"  [{n + 1}] {name}")
        print(f"      URL: {url}")
    
    if API.results:
        # Select first result
        API.select(1, True)
        print(f"\nSelected: {API.cur_url}")
        
        print("\nFetching qualities...")
        API.load()
        
        print(f"\nAvailable qualities:")
        for n, (quality, link) in enumerate(API.qualities.items()):
            print(f"  [{n + 1}] {quality} -> {link}")
        
        if API.qualities:
            # Get direct URL for first quality
            first_quality = list(API.qualities.keys())[0]
            print(f"\nGetting direct URL for {first_quality}...")
            try:
                API.get_direct_url(first_quality)
                print(f"\nDIRECT DOWNLOAD URL: {API.dl_url}")
            except Exception as e:
                print(f"Error getting direct URL: {e}")


def test_series():
    print("\n" + "="*60)
    print("TESTING SERIES MODE: Searching for 'dark' (whole season)")
    print("="*60)
    
    API = Akwam('https://ak.sv/')
    print(f"Resolved base URL: {API.url}")
    
    API.type = 'series'
    API.search('dark')
    
    print(f"\nFound {len(API.results)} results:")
    for n, (name, url) in enumerate(list(API.results.items())[:5]):
        print(f"  [{n + 1}] {name}")
        print(f"      URL: {url}")
    
    if API.results:
        # Select first result
        API.select(1, True)
        print(f"\nSelected: {API.cur_url}")
        
        print("\nFetching episodes...")
        API.fetch_episodes()
        
        print(f"\nFound {len(API.results)} episodes:")
        for n, (name, url) in enumerate(list(API.results.items())[:10]):
            print(f"  [{n + 1}] {name}")
        
        if API.results:
            print("\n>>> Getting ALL episodes (recursive mode)...")
            episodes = API.recursive_episodes()
            
            print("\n" + "="*60)
            print("ALL EPISODE DIRECT URLS:")
            print("="*60)
            for i, url in enumerate(episodes):
                print(f"  Episode {i+1}: {url}")


if __name__ == '__main__':
    print("AKWAM-DL WORKFLOW TEST")
    print("="*60)
    
    test_movie()
    test_series()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
