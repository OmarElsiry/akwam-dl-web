import re, os
from requests import get

HTTP = 'https://'
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
RGX_QUALITY_TAG = rf'tab-content quality.*?a href="{RGX_DL_URL}"'
RGX_SIZE_TAG = r'font-size-14 mr-auto">([0-9.MGB ]+)</'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def safe_get(url, **kwargs):
    kwargs.setdefault('headers', HEADERS)
    kwargs.setdefault('timeout', 30)
    return get(url, **kwargs)

class AkwamAPI:
    def __init__(self, base_url="https://ak.sv/"):
        # Resolve actual URL if it redirects
        try:
            r = safe_get(base_url)
            url = r.url
        except:
            url = base_url
        self.base_url = [url, url[:-1]][url[-1] == '/']
        self.search_url = self.base_url + '/search?q='

    def search(self, query, type='movie', page=1):
        query = query.replace(' ', '+')
        url = f'{self.search_url}{query}&section={type}&page={page}'
        response = safe_get(url)
        page_content = response.content.decode()
        
        # Simple regex for finding movie/series links
        pattern = rf'({self.base_url}/{type}/\d+/.*?)["\s]'
        matches = re.findall(pattern, page_content)
        
        results = []
        for match in matches:
            # Avoid duplicates and keep it clean
            name = match.split('/')[-1].replace('-', ' ').title()
            if not any(r['url'] == match for r in results):
                results.append({'name': name, 'url': match})
        
        return results

    def get_episodes(self, series_url):
        response = safe_get(series_url)
        page_content = response.content.decode()
        
        pattern = rf'({self.base_url}/episode/\d+/.*?)["\s]'
        matches = re.findall(pattern, page_content)
        
        episodes = []
        for match in matches:
            name = match.split('/')[-1].replace('-', ' ').title()
            if not any(e['url'] == match for e in episodes):
                episodes.append({'name': name, 'url': match})
        
        # Reverse to have them in order usually
        return episodes[::-1]

    def get_qualities(self, content_url):
        response = safe_get(content_url)
        page_text = response.text
        page_content = response.content.decode().replace('\n', '')
        
        qualities_matches = re.findall(RGX_QUALITY_TAG, page_content)
        sizes = re.findall(RGX_SIZE_TAG, page_content)
        
        avail_qualities = []
        q_labels = ['1080p', '720p', '480p', '360p', '240p']
        
        match_idx = 0
        for q in q_labels:
            if f'>{q}</' in page_text and match_idx < len(qualities_matches):
                size = sizes[match_idx] if match_idx < len(sizes) else "Unknown"
                avail_qualities.append({
                    'quality': q,
                    'link_id': qualities_matches[match_idx],
                    'size': size
                })
                match_idx += 1
                
        return avail_qualities

    def resolve_direct_url(self, link_id_url):
        # 1. Access the intermediate download page
        url = HTTP + link_id_url
        r1 = safe_get(url)
        
        # 2. Extract the redirect/shortened URL
        m1 = re.search(RGX_SHORTEN_URL, r1.content.decode())
        if not m1:
            return None
        
        short_url = HTTP + m1.group(1)
        
        # 3. Access the final page containing the direct link
        r2 = safe_get(short_url)
        
        # Sometimes it requires one more redirect or has a meta refresh
        final_html = r2.content.decode()
        if short_url != r2.url:
            r2 = safe_get(r2.url)
            final_html = r2.content.decode()

        # 4. Extract the actual direct file URL
        m2 = re.search(RGX_DIRECT_URL, final_html)
        if not m2:
            return None
            
        return HTTP + m2.group(1)
