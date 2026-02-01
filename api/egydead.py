from fastapi import FastAPI
import re
import requests
from typing import Optional
from urllib.parse import quote, unquote

app = FastAPI()

class EgyDeadAPI:
    def __init__(self):
        self.base_url = "https://egydead.skin"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search(self, query):
        encoded_query = quote(query)
        url = f"{self.base_url}/?s={encoded_query}"
        resp = requests.get(url, headers=self.headers)
        results = []
        movie_items = re.findall(r'<li class="movieItem">(.*?)</li>', resp.text, re.DOTALL)
        for item in movie_items:
            link_match = re.search(r'<a href="(.*?)"', item)
            title_match = re.search(r'<h1 class="BottomTitle">(.*?)</h1>', item)
            image_match = re.search(r'<img src="(.*?)"', item)
            if link_match and title_match:
                results.append({
                    'url': link_match.group(1),
                    'title': title_match.group(1),
                    'image': image_match.group(1) if image_match else None
                })
        return results

    def get_links(self, url):
        resp = requests.get(url, headers=self.headers)
        links = []
        pattern1 = r'<span class="ser-name">(.*?)</span>.*?(?:<em>(.*?)</em>.*?)?href="(.*?)"'
        matches = re.findall(pattern1, resp.text, re.DOTALL)
        for match in matches:
            links.append({
                'server': match[0].strip(),
                'quality': match[1].strip() if match[1] else "Unknown",
                'url': match[2].strip()
            })
        if not links:
            items = re.findall(r'<a href="([^"]+)"[^>]*class="downloadv-item"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            for href, content in items:
                name_match = re.search(r'<div class="name">(.*?)</div>', content)
                server = name_match.group(1).strip() if name_match else "Unknown"
                quality = "Unknown"
                if "1080" in content: quality = "1080p"
                elif "720" in content: quality = "720p"
                elif "480" in content: quality = "480p"
                links.append({'server': server, 'quality': quality, 'url': href})
        
        episodes = []
        ep_links = re.findall(r'href="([^"]*/episode/[^"]+)"', resp.text)
        seen = set()
        for l in ep_links:
            if any(x in l.lower() for x in ['facebook', 'twitter', 'whatsapp', 'telegram', 'pinterest', 'reddit']):
                continue
            if l not in seen:
                seen.add(l)
                title = unquote(l.split('/')[-2]).replace('-', ' ').title()
                episodes.append({'url': l, 'title': title})
        return {"links": links, "episodes": episodes}

egy = EgyDeadAPI()

@app.get("/api/egydead")
@app.get("/")
async def handle_egydead(
    action: str, 
    q: Optional[str] = None, 
    url: Optional[str] = None
):
    if action == 'search':
        return egy.search(q)
    elif action == 'details':
        return egy.get_links(url)
    return {"error": "Invalid action"}
