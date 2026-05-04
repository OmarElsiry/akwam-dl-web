import re, os
from requests import get

HTTP = 'https://'
RGX_DL_URL = r'https?://([\w.-]+/link/\d+)'
# Matches the first download server URL in the /link/ page
RGX_SHORTEN_URL = r'https?://([\w.-]+/download/[^"]+)"'
# Matches a direct file URL with a download attribute (legacy sites)
RGX_DIRECT_URL = r'https?://([^"]+)"\s+download'
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
        
        # More flexible pattern for episode links, accounting for potential variations in Akwam URL structure
        pattern = rf'({self.base_url}/episode/\d+[^"\s]*)'
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

    def get_download_links(self, link_id_url):
        """
        Returns all available download server URLs from the /link/ page.
        Akwam lists multiple CDN servers (main + mirrors) on this page.
        The returned URLs are the akwam /download/ pages — users click them
        and wait for the countdown to get the actual file.
        """
        url = HTTP + link_id_url
        try:
            r = safe_get(url)
            html = r.content.decode('utf-8', errors='replace')
        except Exception:
            return []

        # Find all unique /download/ hrefs (multiple CDN servers)
        raw = re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html)
        seen = set()
        servers = []
        for u in raw:
            if u not in seen:
                seen.add(u)
                servers.append(u)
        return servers

    def resolve_direct_url(self, link_id_url):
        """
        Attempts to resolve a direct file URL from an akwam link_id.

        Akwam's download flow:
          1. go.akwam.com.co/link/{id}  — lists download server buttons
          2. akwam.com.co/download/...  — JS-gated countdown page (2.2s timer)
          3. Actual .mp4 file URL       — injected by obfuscated JS, not in HTML

        Because step 3 requires JavaScript execution, we fall back to returning
        the most accessible download page URL (step 2 / main server) so users
        can open it in a browser to complete the download.
        """
        url = HTTP + link_id_url

        try:
            r1 = safe_get(url)
            html1 = r1.content.decode('utf-8', errors='replace')
        except Exception:
            return None

        # Collect all download server links from the /link/ page
        raw_links = re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)
        seen = set()
        dl_links = []
        for u in raw_links:
            if u not in seen:
                seen.add(u)
                dl_links.append(u)

        if not dl_links:
            # Last resort: return the /link/ page itself as the download URL
            return url

        # Try following each server link for a direct file redirect
        for dl_url in dl_links:
            try:
                r2 = safe_get(dl_url, allow_redirects=True, timeout=20)
                
                # Check 1: Did the server redirect directly to the file?
                ct = r2.headers.get('content-type', '')
                if any(x in ct for x in ('video', 'octet-stream', 'mp4', 'mkv')):
                    return r2.url
                final = r2.url
                if any(final.endswith(ext) for ext in ('.mp4', '.mkv', '.avi', '.webm', '.m3u8')):
                    return final
                    
                # Check 2: Akwam updated their site to embed the mp4 link in the HTML instead of redirecting
                html2 = r2.content.decode('utf-8', errors='replace')
                mp4_matches = re.findall(r'href=["\']([^"\']+\.mp4)["\']', html2)
                if mp4_matches:
                    return mp4_matches[0]
                    
                mkv_matches = re.findall(r'href=["\']([^"\']+\.mkv)["\']', html2)
                if mkv_matches:
                    return mkv_matches[0]
            except Exception:
                continue

        # None of the servers gave a direct file — return the main download page
        return dl_links[0]
