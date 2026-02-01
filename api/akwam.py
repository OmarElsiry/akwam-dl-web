from fastapi import FastAPI, Query
import re
import requests
from typing import Optional

app = FastAPI()

RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'

class AkwamAPI:
    def __init__(self, base_url="https://ak.sv/"):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search(self, query, _type='movie', page=1):
        search_url = f"{self.base_url}/search?q={query.replace(' ', '+')}&section={_type}&page={page}"
        resp = requests.get(search_url, headers=self.headers)
        pattern = rf'({self.base_url}/{_type}/\d+/.*?)"'
        links = re.findall(pattern, resp.text)
        
        results = []
        for link in links:
            title = link.split('/')[-1].replace('-', ' ').title()
            results.append({
                'title': title,
                'url': link,
                'id': link.split('/')[-2]
            })
        return results

    def get_qualities(self, url):
        resp = requests.get(url, headers=self.headers)
        page = resp.text.replace('\n', '')
        qualities = {}
        blocks = re.findall(r'<div class="tab-content quality.*?>(.*?)</div>', page)
        for block in blocks:
            q_match = re.search(r'>(\d+p)<', block)
            l_match = re.search(rf'href="({RGX_DL_URL})"', block)
            if q_match and l_match:
                qualities[q_match.group(1)] = l_match.group(1)
        return qualities

    def resolve_link(self, short_url):
        if not short_url.startswith('http'):
            short_url = 'https://' + short_url
        resp = requests.get(short_url, headers=self.headers)
        shorten_match = re.search(RGX_SHORTEN_URL, resp.text)
        if not shorten_match:
            return None
        target_url = 'https://' + shorten_match.group(1)
        resp = requests.get(target_url, headers=self.headers)
        if resp.url != target_url:
            resp = requests.get(resp.url, headers=self.headers)
        direct_match = re.search(RGX_DIRECT_URL, resp.text)
        if direct_match:
            return 'https://' + direct_match.group(1)
        return None

akwam = AkwamAPI()

@app.get("/api/akwam")
@app.get("/")
async def handle_akwam(
    action: str, 
    q: Optional[str] = None, 
    type: Optional[str] = "movie", 
    url: Optional[str] = None
):
    if action == 'search':
        return akwam.search(q, type)
    elif action == 'details':
        return akwam.get_qualities(url)
    elif action == 'resolve':
        return {"direct_url": akwam.resolve_link(url)}
    return {"error": "Invalid action"}
