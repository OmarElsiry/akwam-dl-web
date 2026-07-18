"""
Find an EgyDead movie page that has multiple qualities (1080p, 720p, 480p)
in its donwload-servers-list, then print the full structure.
"""
import sys, re
sys.path.insert(0, 'api')
from egydead_api import EgyDeadAPI

api = EgyDeadAPI()

# Try a few different films - older ones tend to have multiple quality options
TEST_URLS = [
    'https://tv8.egydead.live/avengers-endgame-2019/',
    'https://tv8.egydead.live/avatar-the-way-of-water-2022/',
    'https://tv8.egydead.live/oppenheimer-2023/',
]

for url in TEST_URLS:
    print(f"\n=== {url} ===")
    try:
        data = api.get_watch_url(url)
        quals = set(d['quality'] for d in data['downloads'])
        print(f"  servers: {len(data['servers'])}  downloads: {len(data['downloads'])}  unique qualities: {quals}")
        for d in data['downloads']:
            print(f"    [{d['quality']}] {d['name']} -> {d['url'][:60].encode('ascii','replace').decode()}")
    except Exception as e:
        print(f"  Error: {e}")
