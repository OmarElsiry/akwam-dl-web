import re
import os
from firecrawl import Firecrawl

FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "fc-186b4e776b4042dfa4043a97c4985cc9")

# Video hosting services to recognize iframes
VIDEO_HOSTS = [
    'uqload', 'dood', 'streamtape', 'upstream', 'vidoza', 'voe.sx',
    'mixdrop', 'filemoon', 'ok.ru', 'dailymotion', 'vk.com', 'player',
    'embed', 'video', 'stream', 'watch', 'play', 'vid', 'media',
    'streamhub', 'vidlox', 'vidhide', 'openvid', 'sendvid', 'sbplay',
    'sbembed', 'cloudemb', 'streamlare', 'supervideo'
]

SKIP_URL_PARTS = ['/type/', '?s=', '/page/', '/dmca', '#', '/wp-', '/feed']


class EgyDeadAPI:
    """Scrapes egydead.live for Arabic-dubbed/subbed movies and series."""

    def __init__(self):
        self.client = Firecrawl(api_key=FIRECRAWL_API_KEY)
        self.search_base = "https://egydead.live"

    # ------------------------------------------------------------------ #
    #  Search
    # ------------------------------------------------------------------ #

    def search(self, query: str) -> list:
        """Search EgyDead for any content type."""
        search_url = f"{self.search_base}/?s={query.replace(' ', '+')}"
        result = self.client.scrape(search_url, formats=['markdown'])
        return self._parse_search_results(result.markdown or '')

    def _parse_search_results(self, markdown: str) -> list:
        results = []
        seen_urls: set = set()

        # Each result row looks like:
        # **Title text** category text](https://tv8.egydead.live/slug/ "title")
        pattern = r'\*\*([^*\n]+)\*\*[^\]]*\]\((https?://[^)\s"]+)'
        matches = re.findall(pattern, markdown)

        for title, url in matches:
            # Normalise trailing slash
            url = url.rstrip('/') + '/'
            if url in seen_urls:
                continue
            if any(skip in url for skip in SKIP_URL_PARTS):
                continue

            seen_urls.add(url)
            content_type = self._classify_url(url)
            clean_title = self._clean_title(title)

            results.append({
                'name': clean_title,
                'url': url,
                'type': content_type,
                'source': 'egydead'
            })

        return results

    # ------------------------------------------------------------------ #
    #  Navigation helpers
    # ------------------------------------------------------------------ #

    def get_seasons(self, series_url: str) -> list:
        """Return seasons for a series page."""
        result = self.client.scrape(series_url, formats=['markdown'])
        return self._parse_links_by_type(result.markdown or '', '/season/')

    def get_episodes(self, season_url: str) -> list:
        """Return episodes for a season page (oldest first)."""
        result = self.client.scrape(season_url, formats=['markdown'])
        episodes = self._parse_links_by_type(result.markdown or '', '/episode/')
        return episodes[::-1]   # reverse so ep 1 is first

    def _parse_links_by_type(self, markdown: str, url_filter: str) -> list:
        items = []
        seen: set = set()
        pattern = r'\*\*([^*\n]+)\*\*[^\]]*\]\((https?://[^)\s"]+)'
        for title, url in re.findall(pattern, markdown):
            url = url.rstrip('/') + '/'
            if url in seen or url_filter not in url:
                continue
            seen.add(url)
            items.append({'name': title.strip(), 'url': url})
        return items

    # ------------------------------------------------------------------ #
    #  Watch / Stream URL extraction
    # ------------------------------------------------------------------ #

    def get_watch_url(self, content_url: str) -> dict:
        """Scrape a movie/episode page and return embed or direct video URLs."""
        result = self.client.scrape(content_url, formats=['html', 'markdown'])
        html = result.html or ''

        # 1. iframes (most common – external player)
        all_iframes = re.findall(
            r'<iframe[^>]+src=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        embed_urls = [
            src for src in all_iframes
            if any(h in src.lower() for h in VIDEO_HOSTS)
            and 'recaptcha' not in src
            and 'facebook.com/plugins' not in src
        ]

        # 2. Direct video files (.mp4 / .m3u8)
        direct_urls = list(dict.fromkeys(re.findall(
            r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*)',
            html
        )))

        # 3. Fallback – try data-src attributes
        if not embed_urls:
            ds = re.findall(r'data-src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            embed_urls = [u for u in ds if any(h in u.lower() for h in VIDEO_HOSTS)]

        return {
            'embed_urls': embed_urls[:5],
            'direct_urls': direct_urls[:3],
            'page_url': content_url
        }

    # ------------------------------------------------------------------ #
    #  Utilities
    # ------------------------------------------------------------------ #

    @staticmethod
    def _classify_url(url: str) -> str:
        if '/episode/' in url:
            return 'episode'
        if '/season/' in url:
            return 'season'
        if '/serie/' in url:
            return 'series'
        if '/assembly/' in url:
            return 'collection'
        return 'movie'

    @staticmethod
    def _clean_title(title: str) -> str:
        title = title.strip()
        # Strip Arabic watch prefixes
        title = re.sub(
            r'^(مشاهدة\s+)?(فيلم|مسلسل|كرتون|سلسلة|جميع مواسم|كل مواسم)\s+',
            '', title
        )
        # Strip Arabic quality/langue suffixes
        title = re.sub(
            r'\s+(مترجم|مدبلج|كامل|مترجمة)(\s+.*)?$',
            '', title
        )
        return title.strip()
