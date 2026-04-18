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
        self._cache = {}

    # ------------------------------------------------------------------ #
    #  Search
    # ------------------------------------------------------------------ #

    def search(self, query: str) -> list:
        """Search EgyDead for any content type."""
        search_url = f"{self.search_base}/?s={query.replace(' ', '+')}"
        if search_url in self._cache:
            return self._cache[search_url]
        result = self.client.scrape(search_url, formats=['markdown'])
        res = self._parse_search_results(getattr(result, 'markdown', '') or '')
        self._cache[search_url] = res
        return res

    def _parse_search_results(self, markdown: str) -> list:
        """Parse search result links from markdown."""
        results = []
        seen = set()
        # Find ALL links in the format ](URL "Hover text")
        pattern = r'\]\((https?://[^\s)]+)(?:\s+"([^"]+)")?\)'
        
        from urllib.parse import unquote
        for url, hover_title in re.findall(pattern, markdown):
            url = url.rstrip('/') + '/'
            
            slug = url.rstrip('/').split('/')[-1]
            # Use hover title if available, else deduce from URL slug
            if hover_title:
                name = hover_title.strip()
            else:
                name = unquote(slug).replace('-', ' ').strip()
            
            # Skip root domain
            if 'egydead' in slug.lower() and '.' in slug:
                continue
            if 'egydead' in name.lower() and '.' in name:
                continue
            
            skip = False
            for part in SKIP_URL_PARTS:
                if part in url:
                    skip = True
                    break
            
            if name and url not in seen and not skip:
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
        cache_key = f"seasons:{series_url}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        result = self.client.scrape(series_url, formats=['markdown'])
        res = self._parse_links_by_type(getattr(result, 'markdown', '') or '', '/season/')
        self._cache[cache_key] = res
        return res

    def get_episodes(self, season_url: str) -> list:
        """Return episodes for a season page (oldest first)."""
        cache_key = f"episodes:{season_url}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        result = self.client.scrape(season_url, formats=['markdown'])
        md = getattr(result, 'markdown', '') or ''
        
        # Check if we were redirected to the homepage (common EgyDead bot protection)
        title = getattr(result.metadata, 'title', '') if hasattr(result, 'metadata') else ''
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
             print(f"Fallback search found {len(search_results)} total items.")
             
             # Map search results that are episodes
             episodes = [r for r in search_results if r['type'] == 'episode']
             if not episodes:
                 # If no episodes, fallback to any link containing /episode/
                 episodes = [{'name': r['name'], 'url': r['url']} for r in search_results if '/episode/' in r['url']]
             
             if episodes:
                 # Sort by episode number if possible, or leave as found
                 res = episodes[::-1]
                 self._cache[cache_key] = res
                 return res
             else:
                 print(f"Fallback search for {query} returned no episode-type results.")

        episodes = self._parse_links_by_type(md, '/episode/')
        res = episodes[::-1]
        self._cache[cache_key] = res
        return res

    def _parse_links_by_type(self, markdown: str, type_filter: str) -> list:
        """Extract links from markdown that match a specific URL path (e.g. /episode/)."""
        items = []
        seen = set()
        # Find ALL links in the format ](URL "Hover text")
        pattern = r'\]\((https?://[^\s)]+)(?:\s+"([^"]+)")?\)'
        
        from urllib.parse import unquote
        for link, hover_title in re.findall(pattern, markdown):
            link = link.rstrip('/') + '/'
            
            # Use hover title if available, else deduce from URL slug
            if hover_title:
                name = hover_title.strip()
            else:
                slug = link.rstrip('/').split('/')[-1]
                name = unquote(slug).replace('-', ' ').strip()
            
            if name and link not in seen and type_filter in link:
                seen.add(link)
                items.append({'name': name, 'url': link})
        return items

    # ------------------------------------------------------------------ #
    #  Watch / Stream URL extraction
    # ------------------------------------------------------------------ #

    def get_watch_url(self, content_url: str) -> dict:
        """Scrape a movie/episode page and return embed or direct video URLs."""
        cache_key = f"watch:{content_url}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Use actions to click the watch/download button to expose the servers
        result = self.client.scrape(content_url, formats=['html'], actions=[
            {"type": "click", "selector": ".watchNow button"},
            {"type": "wait", "milliseconds": 500},
        ])
        
        # Handle dictionary return if SDK version is old/different
        html = result.get('html', '') if isinstance(result, dict) else getattr(result, 'html', '')
        html = html or ''

        # 1. Parse Servers from the "serversList" injected by the button click
        servers = []
        # Pattern looks for <li data-link="URL">...<p>ServerName</p>...</li>
        pattern = r'<li[^>]*data-link=["\']([^"\']+)["\'][^>]*>.*?<p>([^<]+)</p>'
        for match in re.finditer(pattern, html, re.DOTALL | re.IGNORECASE):
            url, name = match.groups()
            servers.append({'name': name.strip(), 'url': url.strip()})

        # 2. Extract Downloads from the "donwload-servers-list"
        downloads = []
        dl_block_match = re.search(r'<ul[^>]*class=["\'][^"\']*donwload-servers-list[^"\']*["\'][^>]*>(.*?)</ul>', html, re.DOTALL | re.IGNORECASE)
        if dl_block_match:
            for li_html in re.split(r'</li>', dl_block_match.group(1), flags=re.IGNORECASE):
                # We skip empty tail fragments
                if not li_html.strip(): continue
                name_m = re.search(r'<span[^>]*class=["\'][^"\']*ser-name[^"\']*["\'][^>]*>(.*?)</span>', li_html, re.IGNORECASE | re.DOTALL)
                qual_m = re.search(r'<div[^>]*class=["\'][^"\']*server-info[^"\']*["\'][^>]*>.*?<em[^>]*>(.*?)</em>', li_html, re.IGNORECASE | re.DOTALL)
                url_m = re.search(r'<a[^>]*href=["\']([^"\']+)["\']', li_html, re.IGNORECASE)
                
                if qual_m and url_m:
                    name = name_m.group(1).strip() if name_m and name_m.group(1).strip() else "Direct Download"
                    downloads.append({
                        'name': name,
                        'quality': qual_m.group(1).strip(),
                        'url': url_m.group(1).strip()
                    })

        # Deduplicate by URL (page HTML sometimes has the list twice — live + commented copy)
        seen_urls = set()
        unique_downloads = []
        for d in downloads:
            if d['url'] not in seen_urls:
                seen_urls.add(d['url'])
                unique_downloads.append(d)
        downloads = unique_downloads

        # 3. Fallback: Parse iframes (most common – external player)
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

        # 4. Direct video files (.mp4 / .m3u8) (fallback for direct play)
        direct_urls = list(dict.fromkeys(re.findall(
            r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*)',
            html
        )))

        # 5. Fallback – try data-src attributes
        if not servers and not direct_urls:
            ds = re.findall(r'data-src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            embed_urls = [u for u in ds if any(h in u.lower() for h in VIDEO_HOSTS)]
            for i, url in enumerate(embed_urls[:5]):
                servers.append({'name': f'Server {i+1}', 'url': url})

        ret = {
            'servers': servers,
            'downloads': downloads,
            'direct_urls': direct_urls[:3],
            'page_url': content_url
        }
        self._cache[cache_key] = ret
        return ret
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
