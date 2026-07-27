import html as html_lib
import re
import warnings
from urllib.parse import urljoin, urlparse

from requests import get
from requests.exceptions import SSLError
from urllib3.exceptions import InsecureRequestWarning

HTTP = 'https://'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def safe_get(url, **kwargs):
    kwargs.setdefault('headers', HEADERS)
    kwargs.setdefault('timeout', 30)
    return get(url, **kwargs)


def _is_downet_url(url):
    """Return True only for Downet's CDN itself, never lookalike hosts."""
    hostname = (urlparse(url).hostname or '').lower().rstrip('.')
    return hostname == 'downet.net' or hostname.endswith('.downet.net')


def _extract_media_url(page_html, page_url):
    """Extract an MP4/MKV URL from an Akwam watch or download page."""
    media_url = r'([^"\']+\.(?:mp4|mkv)(?:\?[^"\']*)?)'
    patterns = (
        rf'<source\b[^>]*\bsrc=["\']{media_url}["\']',
        rf'<a\b[^>]*\bhref=["\']{media_url}["\'][^>]*\bdownload\b',
        rf'<a\b[^>]*\bhref=["\']{media_url}["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, page_html, re.IGNORECASE)
        if match:
            return urljoin(page_url, html_lib.unescape(match.group(1)))
    return None


def _get_downet_media(session, media_url, **kwargs):
    """Fetch media with a host-scoped fallback for Downet's broken TLS chain."""
    try:
        return session.get(media_url, **kwargs)
    except SSLError:
        if not _is_downet_url(media_url):
            raise

        # Downet currently sends an incomplete certificate chain from some CDN
        # shards. Keep verification enabled everywhere else and retry only this
        # exact provider host so Akwam playback can still use byte ranges.
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            return session.get(media_url, verify=False, **kwargs)

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

            # Akwam watch pages expose every quality as <source> tags with the
            # highest quality first, even when the selected watch URL belongs
            # to a lower quality.  The matching download page is quality-
            # specific, so use it for resolution and protected playback.
            link_id = dl_url or watch_url or ''

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

            return _extract_media_url(html, r.url)
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

            media_url = _extract_media_url(html, r.url)
            if media_url and _is_downet_url(media_url):
                return session, media_url, r.url

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
            resp = _get_downet_media(
                session,
                mp4_url,
                headers=headers,
                stream=True,
                timeout=(15, 300),
            )
            content_type = resp.headers.get('content-type', '').split(';', 1)[0].lower()
            if not content_type or content_type == 'application/octet-stream':
                media_path = urlparse(mp4_url).path.lower()
                if media_path.endswith('.mp4'):
                    content_type = 'video/mp4'
                elif media_path.endswith('.mkv'):
                    content_type = 'video/x-matroska'
                else:
                    content_type = 'application/octet-stream'
            info = {
                'status_code': resp.status_code,
                'content_type': content_type,
                'content_length': resp.headers.get('content-length'),
                'content_range': resp.headers.get('content-range'),
                'accept_ranges': resp.headers.get('accept-ranges', 'bytes'),
            }
            return resp, info
        except Exception:
            return None, None
