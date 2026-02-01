from http.server import BaseHTTPRequestHandler
import json
import re
import requests
from urllib.parse import urlparse, parse_qs

RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'

class Akwam:
    def __init__(self, base_url="https://ak.sv/"):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search(self, query, _type='movie', page=1):
        search_url = f"{self.base_url}/search?q={query.replace(' ', '+')}&section={_type}&page={page}"
        resp = requests.get(search_url, headers=self.headers)
        
        # Regex for results
        # Need to capture title and link
        # Based on akwam-dl.py: rf'({self.url}/{self.type}/\d+/.*?)"'
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
        
        # RGX_QUALITY_TAG = rf'tab-content quality.*?a href="{RGX_DL_URL}"'
        quality_pattern = rf'tab-content quality.*?a href="({RGX_DL_URL})"'
        matches = re.findall(quality_pattern, page)
        
        qualities = {}
        # Simple mapping for common qualities
        for q in ['1080p', '720p', '480p']:
            if f'>{q}</' in resp.text:
                # This logic is a bit brittle in the original script
                # It assumes the order of matches matches the presence of quality tags
                pass
        
        # Better extraction: find all quality blocks
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
            
        # Step 1: Solving shortened URL
        resp = requests.get(short_url, headers=self.headers)
        shorten_match = re.search(RGX_SHORTEN_URL, resp.text)
        if not shorten_match:
            return None
        
        # Step 2: Getting Direct URL
        target_url = 'https://' + shorten_match.group(1)
        resp = requests.get(target_url, headers=self.headers)
        
        # Fix non-direct URL
        if resp.url != target_url:
            resp = requests.get(resp.url, headers=self.headers)
            
        direct_match = re.search(RGX_DIRECT_URL, resp.text)
        if direct_match:
            return 'https://' + direct_match.group(1)
        return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        action = query_params.get('action', [None])[0]
        akwam = Akwam()
        
        response_data = {"error": "Invalid action"}
        status_code = 400
        
        try:
            if action == 'search':
                q = query_params.get('q', [''])[0]
                t = query_params.get('type', ['movie'])[0]
                results = akwam.search(q, t)
                response_data = results
                status_code = 200
            
            elif action == 'details':
                url = query_params.get('url', [None])[0]
                if url:
                    qualities = akwam.get_qualities(url)
                    response_data = qualities
                    status_code = 200
            
            elif action == 'resolve':
                url = query_params.get('url', [None])[0]
                if url:
                    direct_url = akwam.resolve_link(url)
                    response_data = {"direct_url": direct_url}
                    status_code = 200
        except Exception as e:
            response_data = {"error": str(e)}
            status_code = 500

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
