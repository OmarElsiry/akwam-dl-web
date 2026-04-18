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
        """Parse search result links from markdown."""
        results = []
        seen = set()
        # Hyper-robust pattern: **Title**](URL)
        pattern = r'\*\*([^*]+)\*\*\]\((https?://[^ )\s\"]+)'
        
        for name, url in re.findall(pattern, markdown, re.IGNORECASE):
            url = url.rstrip('/') + '/'
            if url not in seen and '/wp-content/' not in url:
                seen.add(url)
                # Determine type from URL
                ctype = 'movie'
                if '/series/' in url:    ctype = 'series'
                elif '/season/' in url:  ctype = 'season'
                elif '/episode/' in url: ctype = 'episode'
                
                results.append({
                    'name': name.strip(),
                    'url': url,
                    'type': ctype,
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
        md = result.markdown or ''
        
        # Check if we were redirected to the homepage (common EgyDead bot protection)
        title = result.metadata.title or ''
        is_homepage = "ايجي ديد" in title and "مشاهدة" not in title and "نتائج البحث" not in title
        
        if is_homepage:
             # Extract slug from URL to use as search query
             # e.g. /season/batman-caped-crusader-season-1/ -> batman caped crusader
             slug = season_url.rstrip('/').split('/')[-1]
             query = slug.replace('-', ' ')
             # Broaden query by removing 'season' or 'episode' suffixes
             if 'season' in query: query = query.split('season')[0].strip()
             if 'episode' in query: query = query.split('episode')[0].strip()
             
             print(f"Redirect (homepage) detected. Falling back to search for: {query}")
             search_results = self.search(query)
             # Map search results that are episodes
             episodes = [r for r in search_results if '/episode/' in r['url']]
             if episodes:
                 return episodes[::-1]
             else:
                 print(f"Fallback search for {query} returned no episodes.")

        episodes = self._parse_links_by_type(md, '/episode/')
        return episodes[::-1]

    def _parse_links_by_type(self, markdown: str, type_filter: str) -> list:
        """Extract links from markdown that match a specific URL path (e.g. /episode/)."""
        items = []
        seen = set()
        # Hyper-robust pattern: **Title**](URL)
        pattern = r'\*\*([^*]+)\*\*\]\((https?://[^ )\s\"]+)'
        
        for title, link in re.findall(pattern, markdown):
            link = link.rstrip('/') + '/'
            if link not in seen and type_filter in link:
                seen.add(link)
                items.append({'name': title.strip(), 'url': link})
        return items

    # ------------------------------------------------------------------ #
    #  Watch / Stream URL extraction
    # ------------------------------------------------------------------ #

    def get_watch_url(self, content_url: str) -> dict:
        """Scrape a movie/episode page and return embed or direct video URLs."""
        # Use actions to click the watch/download button to expose the servers
        result = self.client.scrape(content_url, formats=['html', 'markdown'], actions=[
            {"type": "wait", "milliseconds": 2000},
            {"type": "click", "selector": ".watchNow button"},
            {"type": "wait", "milliseconds": 3000},
        ])
        html = result.html or ''

        # 1. Parse Servers from the "serversList" injected by the button click
        servers = []
        # Pattern looks for <li data-link="URL">...<p>ServerName</p>...</li>
        pattern = r'<li[^>]*data-link=["\']([^"\']+)["\'][^>]*>.*?<p>([^<]+)</p>'
        for match in re.finditer(pattern, html, re.DOTALL | re.IGNORECASE):
            url, name = match.groups()
            servers.append({'name': name.strip(), 'url': url.strip()})

        # 2. Fallback: Parse iframes (most common – external player)
        if not servers:
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
            for i, url in enumerate(embed_urls[:5]):
                servers.append({'name': f'Server {i+1}', 'url': url})

        # 3. Direct video files (.mp4 / .m3u8) (fallback for direct play)
        direct_urls = list(dict.fromkeys(re.findall(
            r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*)',
            html
        )))

        # 4. Fallback – try data-src attributes
        if not servers and not direct_urls:
            ds = re.findall(r'data-src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            embed_urls = [u for u in ds if any(h in u.lower() for h in VIDEO_HOSTS)]
            for i, url in enumerate(embed_urls[:5]):
                servers.append({'name': f'Server {i+1}', 'url': url})

        return {
            'servers': servers,
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
