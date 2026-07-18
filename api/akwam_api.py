import re
from requests import get

HTTP = 'https://'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def safe_get(url, **kwargs):
    kwargs.setdefault('headers', HEADERS)
    kwargs.setdefault('timeout', 30)
    return get(url, **kwargs)

class AkwamAPI:
    def __init__(self, base_url="https://ak.sv/"):
        try:
            r = safe_get(base_url)
            self.base_url = r.url.rstrip('/')
        except:
            self.base_url = base_url.rstrip('/')
        self.search_url = self.base_url + '/search?q='

    def search(self, query, type='movie', page=1):
        query = query.replace(' ', '+')
        url = f'{self.search_url}{query}&section={type}&page={page}'
        response = safe_get(url)
        page_content = response.content.decode()
        pattern = rf'({self.base_url}/{type}/\d+/.*?)["\s]'
        matches = re.findall(pattern, page_content)
        results = []
        for match in matches:
            name = match.split('/')[-1].replace('-', ' ').title()
            if not any(r['url'] == match for r in results):
                results.append({'name': name, 'url': match})
        return results

    def get_episodes(self, series_url):
        response = safe_get(series_url)
        page_content = response.content.decode()
        pattern = rf'({self.base_url}/episode/\d+[^"\s]*)'
        matches = re.findall(pattern, page_content)
        episodes = []
        for match in matches:
            name = match.split('/')[-1].replace('-', ' ').title()
            if not any(e['url'] == match for e in episodes):
                episodes.append({'name': name, 'url': match})
        return episodes[::-1]

    def get_qualities(self, content_url):
        """Parse quality tabs from an Akwam movie/series page.

        New site structure:
          - Tab labels: <li><a href="#tab-4" class="selected">720p</a></li>
          - Watch link: <a href="https://akwam.it/watch/{id}/{movie_id}/{slug}">مشاهدة</a>
          - Download link: <a href="https://akwam.it/download/{id}/{movie_id}/{slug}">تحميل</a>
          - Size: <span class="font-size-14 mr-auto">863.1 MB</span>
        """
        response = safe_get(content_url)
        html = response.content.decode('utf-8', errors='replace')

        # Extract quality tabs: tab id -> quality label
        tab_pattern = re.compile(r'<a\s+href="#(tab-\d+)"[^>]*>\s*(\d+p)\s*</a>')
        tab_matches = tab_pattern.findall(html)

        avail_qualities = []
        for tab_id, quality_label in tab_matches:
            # Find the tab-content div for this tab
            tab_block_pattern = re.compile(
                rf'<div\s+class="tab-content\s+quality"[^>]*?id="{re.escape(tab_id)}"[^>]*>'
                r'(.*?)</div>\s*</div>',
                re.DOTALL
            )
            tab_block = tab_block_pattern.search(html)
            if not tab_block:
                continue

            tab_html = tab_block.group(1)

            # Extract watch URL
            watch_match = re.search(
                r'<a\s+href="(https?://[^"]+/watch/\d+/[^"]+)"[^>]*class="[^"]*link-show[^"]*"',
                tab_html
            )
            watch_url = watch_match.group(1) if watch_match else None

            # Extract download URL and size
            dl_match = re.search(
                r'<a\s+href="(https?://[^"]+/download/\d+/[^"]+)"[^>]*class="[^"]*link-download[^"]*">'
                r'.*?<span\s+class="font-size-14\s+mr-auto">([^<]+)</span>',
                tab_html,
                re.DOTALL
            )
            dl_url = dl_match.group(1) if dl_match else None
            size = dl_match.group(2).strip() if dl_match else 'Unknown'

            link_id = watch_url or dl_url or ''

            avail_qualities.append({
                'quality': quality_label,
                'link_id': link_id,
                'watch_url': watch_url or '',
                'download_url': dl_url or '',
                'size': size,
            })

        return avail_qualities

    def get_download_links(self, content_url_or_link_id):
        """Return all download URLs from the quality tabs."""
        if content_url_or_link_id.startswith('http'):
            qualities = self.get_qualities(content_url_or_link_id)
            return [q['download_url'] for q in qualities if q['download_url']]
        return []

    def resolve_direct_url(self, target_url):
        """Extract the direct .mp4 URL from a watch or download page.

        Watch page: <source src="https://s{id}.downet.net/.../{slug}.mp4" ...>
        Download page: <a href="https://s{id}.downet.net/.../{slug}.mp4" download ...>
        """
        if not target_url:
            return None
        if not target_url.startswith('http'):
            target_url = HTTP + target_url

        try:
            r = safe_get(target_url)
            html = r.content.decode('utf-8', errors='replace')

            # Check for <source src="...mp4" in video player
            src_match = re.search(r'<source\s+src=["\']([^"\']+\.mp4)["\']', html)
            if src_match:
                return src_match.group(1)

            # Check for <a href="...mp4" download
            href_match = re.search(r'href=["\']([^"\']+\.mp4)["\'][^>]*download', html)
            if href_match:
                return href_match.group(1)

            # Check for any .mp4 href
            any_mp4 = re.search(r'href=["\']([^"\']+\.mp4)["\']', html)
            if any_mp4:
                return any_mp4.group(1)

            # Check for any .mkv href
            any_mkv = re.search(r'href=["\']([^"\']+\.mkv)["\']', html)
            if any_mkv:
                return any_mkv.group(1)

            return None
        except Exception:
            return None

    def get_fresh_stream_url(self, target_url):
        """Fetch direct mp4 URL preserving cookies for CDN access."""
        import requests as _req
        if not target_url.startswith('http'):
            target_url = HTTP + target_url

        session = _req.Session()
        session.headers.update(HEADERS)
        try:
            r = session.get(target_url, timeout=30)
            html = r.content.decode('utf-8', errors='replace')

            src_match = re.search(r'<source\s+src=["\']([^"\']+\.mp4)["\']', html)
            if src_match:
                return session, src_match.group(1), target_url

            href_match = re.search(r'href=["\']([^"\']+\.mp4)["\'][^>]*download', html)
            if href_match:
                return session, href_match.group(1), target_url

            return None, None, None
        except Exception:
            return None, None, None

    def stream_video(self, target_url, range_header=None):
        """Resolve and stream from a watch/download page."""
        session, mp4_url, page_url = self.get_fresh_stream_url(target_url)
        if not mp4_url:
            return None, None

        headers = {
            'Referer': page_url or target_url,
            'Accept': '*/*',
        }
        if range_header:
            headers['Range'] = range_header

        try:
            resp = session.get(mp4_url, headers=headers, stream=True, timeout=(15, 300))
            info = {
                'status_code': resp.status_code,
                'content_type': resp.headers.get('content-type', 'video/mp4'),
                'content_length': resp.headers.get('content-length'),
                'content_range': resp.headers.get('content-range'),
                'accept_ranges': resp.headers.get('accept-ranges', 'bytes'),
            }
            return resp, info
        except Exception:
            return None, None
