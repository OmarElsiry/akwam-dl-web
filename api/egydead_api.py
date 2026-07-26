import re, os, time
from urllib.parse import unquote

FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")

VIDEO_HOSTS = [
    'uqload', 'dood', 'streamtape', 'upstream', 'vidoza', 'voe.sx',
    'mixdrop', 'filemoon', 'ok.ru', 'dailymotion', 'vk.com', 'player',
    'embed', 'video', 'stream', 'watch', 'play', 'vid', 'media',
    'streamhub', 'vidlox', 'vidhide', 'openvid', 'sendvid', 'sbplay',
    'sbembed', 'cloudemb', 'streamlare', 'supervideo',
    'hgcloud', 'vibuxer', 'minochinos', 'playmogo', 'forafile',
    'earnvids', 'dsvplay', 'doodstream', 'morencius'
]

TRAILER_HOSTS = ('youtube.com', 'youtu.be', 'vimeo.com')

SKIP_URL_PARTS = ['/type/', '?s=', '/page/', '/dmca', '#', '/wp-', '/feed']

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


class EgyDeadAPI:
    """Scrapes egydead.skin for Arabic-dubbed/subbed movies and series.

    Uses Firecrawl as primary scraper (bypasses Cloudflare),
    with cloudscraper and curl_cffi fallbacks.
    """

    def __init__(self):
        self._fc = None
        self.search_base = "https://egydead.skin"
        self._cache = {}
        self._cs = None
        self._curl = None

    def _get_firecrawl(self):
        if not FIRECRAWL_API_KEY:
            return None
        if self._fc is None:
            try:
                from firecrawl import Firecrawl
                self._fc = Firecrawl(api_key=FIRECRAWL_API_KEY)
            except Exception:
                self._fc = False
        return self._fc if self._fc else None

    def _get_cloudscraper(self):
        if self._cs is None:
            try:
                import cloudscraper
                self._cs = cloudscraper.create_scraper()
            except Exception:
                self._cs = False
        return self._cs if self._cs else None

    def _get_curl(self):
        if self._curl is None:
            try:
                from curl_cffi import requests as curl_req
                self._curl = curl_req
            except Exception:
                self._curl = False
        return self._curl if self._curl else None

    # ------------------------------------------------------------------ #
    #  Multi-strategy fetch (Firecrawl -> Playwright -> curl -> cloudscraper)
    # ------------------------------------------------------------------ #

    def _fc_scrape(self, url, formats, timeout=45000, wait_for=6000):
        """Scrape via Firecrawl with retry/backoff (handles intermittent
        Cloudflare 'document_antibot' errors)."""
        fc = self._get_firecrawl()
        if not fc:
            return None
        last_err = None
        for attempt in range(3):
            try:
                result = fc.scrape(
                    url, formats=formats, timeout=timeout, wait_for=wait_for
                )
                return result
            except Exception as e:
                last_err = e
                # Back off before retrying — Cloudflare throttles bursts.
                time.sleep(2 * (attempt + 1))
        if last_err:
            print(f"[EgyDead] Firecrawl failed for {url[:70]}: {last_err}")
        return None

    def _fc_result_text(self, result):
        """Return (markdown, html) from a Firecrawl result object."""
        if not result:
            return '', ''
        md = getattr(result, 'markdown', '') or ''
        if isinstance(result, dict):
            html = result.get('html', '') or ''
        else:
            html = getattr(result, 'html', '') or ''
        return md, html

    def _fetch_playwright(self, url, timeout_ms=25000):
        """Fetch a page with a real headless Chromium browser. This executes
        JavaScript, so it can clear Cloudflare's 'Just a moment...' JS challenge
        on environments whose IP isn't hard-blocked (e.g. a normal user machine,
        unlike a flagged datacenter IP). Returns rendered HTML or ''.
        """
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            return ''
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()

                # Block heavy/ad/tracker requests to speed up the challenge.
                def _route(route):
                    u = route.request.url
                    if any(d in u for d in (
                        'doubleclick.net', 'googlesyndication.com',
                        'google-analytics.com', 'googletagmanager.com',
                        'facebook.net', 'exoclick.com', 'popads.net',
                    )):
                        route.abort()
                        return
                    route.continue_()

                page.route("**/*", _route)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                except Exception:
                    pass

                # Poll for real content (Cloudflare challenge resolves to it).
                deadline = time.time() + max(8, min(18, timeout_ms / 1500))
                while time.time() < deadline:
                    html = page.content()
                    if 'movieItem' in html or 'Just a moment' not in html and len(html) > 5000:
                        browser.close()
                        return html
                    page.wait_for_timeout(1000)

                html = page.content()
                browser.close()
                # Return only if it looks like real content, not the challenge.
                if 'Just a moment' in html or len(html) < 2000:
                    return ''
                return html
        except Exception as e:
            print(f"[EgyDead] Playwright fetch failed for {url[:70]}: {e}")
            return ''

    @staticmethod
    def _html_to_md(html: str) -> str:
        """Turn anchor tags into markdown-style links so the existing markdown
        parsers can consume HTML fetched by the browser fallback."""
        if not html:
            return ''
        out = []
        for url, inner in re.findall(
            r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
            html, re.DOTALL | re.IGNORECASE,
        ):
            text = re.sub(r'<[^>]+>', ' ', inner)
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                out.append(f'[{text}]({url} "{text}")')
        return '\n'.join(out)

    def _fetch(self, url, timeout=20):
        """Try multiple strategies to fetch a page."""
        # Strategy 1: Firecrawl (handles Cloudflare via API), with retry.
        result = self._fc_scrape(url, ['markdown', 'html'])
        md, html = self._fc_result_text(result)
        if 'movieItem' in html or len(md) > 500:
            return md, html

        # Strategy 2: Playwright real browser (bypasses JS Cloudflare challenge).
        ph = self._fetch_playwright(url, timeout_ms=timeout * 1000)
        if ph:
            return self._html_to_md(ph), ph

        # Strategy 3: curl_cffi with Chrome impersonation
        curl = self._get_curl()
        if curl:
            try:
                r = curl.get(url, impersonate='chrome120', headers=HEADERS, timeout=timeout)
                if r.status_code == 200:
                    html = r.text
                    if 'movieItem' in html or len(html) > 2000:
                        return '', html
            except Exception:
                pass

        # Strategy 4: cloudscraper (handles basic Cloudflare)
        cs = self._get_cloudscraper()
        if cs:
            try:
                r = cs.get(url, headers=HEADERS, timeout=timeout)
                if r.status_code == 200:
                    html = r.text
                    if 'movieItem' in html or len(html) > 2000:
                        return '', html
            except Exception:
                pass

        return '', ''

    def _fetch_watch_page(self, url: str, timeout=20) -> str:
        """Submit the site's watch form so real servers are rendered."""
        curl = self._get_curl()
        if curl:
            try:
                r = curl.post(
                    url, data={'View': '1'}, impersonate='chrome120',
                    headers=HEADERS, timeout=timeout,
                )
                if r.status_code == 200 and 'serversList' in r.text:
                    return r.text
            except Exception:
                pass

        cs = self._get_cloudscraper()
        if cs:
            try:
                r = cs.post(url, data={'View': '1'}, headers=HEADERS, timeout=timeout)
                if r.status_code == 200 and 'serversList' in r.text:
                    return r.text
            except Exception:
                pass
        return ''

    # ------------------------------------------------------------------ #
    #  Search
    # ------------------------------------------------------------------ #

    def search(self, query: str) -> list:
        """Search EgyDead for any content type."""
        search_url = f"{self.search_base}/?s={query.replace(' ', '+')}"
        if search_url in self._cache:
            return self._cache[search_url]

        md, html = self._fetch(search_url)
        res = self._parse_search_results(md, html)
        self._cache[search_url] = res
        return res

    def _parse_search_results(self, markdown: str, html: str = '') -> list:
        """Parse search result links from markdown, enriched with thumbnails from HTML."""
        results = []
        seen = set()

        # ── Extract thumbnail map from HTML ──
        thumb_map = {}
        if html:
            for m in re.finditer(
                r'<li[^>]*class=["\'][^"\']*movieItem[^"\']*["\'][^>]*>\s*'
                r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>\s*'
                r'<img[^>]*src=["\']([^"\']+)["\']',
                html, re.DOTALL | re.IGNORECASE
            ):
                link_url = m.group(1).rstrip('/') + '/'
                thumb_url = m.group(2).strip()
                if thumb_url and not thumb_url.endswith('.svg'):
                    thumb_map[link_url] = thumb_url

            if not thumb_map:
                for m in re.finditer(
                    r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>\s*'
                    r'(?:<[^>]*>\s*)*'
                    r'<img[^>]*src=["\']([^"\']+)["\']',
                    html, re.DOTALL | re.IGNORECASE
                ):
                    link_url = m.group(1).rstrip('/') + '/'
                    thumb_url = m.group(2).strip()
                    if thumb_url and 'egydead' in link_url and not thumb_url.endswith('.svg'):
                        thumb_map[link_url] = thumb_url

        # ── Parse links from markdown ──
        pattern = r'\]\((https?://[^\s)]+)(?:\s+"([^"]+)")?\)'

        for url, hover_title in re.findall(pattern, markdown):
            url = url.rstrip('/') + '/'

            # Search pages include the whole navigation in their markdown.
            # Real result cards are the links that have poster thumbnails.
            if thumb_map and url not in thumb_map:
                continue

            slug = url.rstrip('/').split('/')[-1]
            if hover_title:
                name = hover_title.strip()
            else:
                name = unquote(slug).replace('-', ' ').strip()

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
                ctype = 'movie'
                if '/series/' in url or '/serie/' in url: ctype = 'series'
                elif '/season/' in url:  ctype = 'season'
                elif '/episode/' in url: ctype = 'episode'

                entry = {
                    'name': name.strip(),
                    'url': url,
                    'type': ctype,
                    'source': 'egydead'
                }
                if url in thumb_map:
                    entry['thumbnail'] = thumb_map[url]
                results.append(entry)
        return results

    # ------------------------------------------------------------------ #
    #  Navigation helpers
    # ------------------------------------------------------------------ #

    def _scrape_md(self, url: str) -> str:
        """Fetch and return markdown from a page."""
        cache_key = f"md:{url}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        # Strategy 1: Firecrawl markdown
        fc = self._get_firecrawl()
        if fc:
            try:
                result = fc.scrape(url, formats=['markdown'], timeout=45000, wait_for=6000)
                md = getattr(result, 'markdown', '') or ''
                if md:
                    self._cache[cache_key] = md
                    return md
            except Exception:
                pass
        # Strategy 2: Firecrawl HTML -> markdown
        if fc:
            try:
                result = fc.scrape(url, formats=['html'], timeout=45000, wait_for=6000)
                html = (result.get('html', '') if isinstance(result, dict)
                        else getattr(result, 'html', '')) or ''
                if html:
                    md = self._html_to_md(html)
                    if md:
                        self._cache[cache_key] = md
                        return md
            except Exception:
                pass
        # Strategy 3: Playwright real browser -> markdown
        ph = self._fetch_playwright(url, timeout_ms=25000)
        if ph:
            md = self._html_to_md(ph)
            if md:
                self._cache[cache_key] = md
                return md
        # Strategy 4: direct fetch fallback
        md, html = self._fetch(url)
        res = md or self._html_to_md(html) or html
        self._cache[cache_key] = res
        return res

    def get_seasons(self, series_url: str) -> list:
        """Return seasons for a series page."""
        cache_key = f"seasons:{series_url}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        md = self._scrape_md(series_url)
        res = self._parse_links_by_type(md, '/season/')
        self._cache[cache_key] = res
        return res

    def get_episodes(self, season_url: str) -> list:
        """Return episodes for a season page (oldest first)."""
        cache_key = f"episodes:{season_url}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        md = self._scrape_md(season_url)

        # Check if we got redirected to homepage
        is_homepage = "ايجي ديد" in md[:500] and "مشاهدة" not in md[:500] and "نتائج البحث" not in md[:500]

        if is_homepage:
            slug = season_url.rstrip('/').split('/')[-1]
            query = slug.replace('-', ' ')
            if 'season' in query: query = query.split('season')[0].strip()
            if 'episode' in query: query = query.split('episode')[0].strip()

            search_results = self.search(query)
            episodes = [r for r in search_results if r['type'] == 'episode']
            if not episodes:
                episodes = [{'name': r['name'], 'url': r['url']} for r in search_results if '/episode/' in r['url']]

            if episodes:
                res = episodes[::-1]
                self._cache[cache_key] = res
                return res

        episodes = self._parse_links_by_type(md, '/episode/')
        res = episodes[::-1]
        self._cache[cache_key] = res
        return res

    def _parse_links_by_type(self, markdown: str, type_filter: str) -> list:
        """Extract links from markdown that match a specific URL path."""
        items = []
        seen = set()
        pattern = r'\]\((https?://[^\s)]+)(?:\s+"([^"]+)")?\)'

        for link, hover_title in re.findall(pattern, markdown):
            link = link.rstrip('/') + '/'
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

        servers, downloads, direct_urls = [], [], []

        # Attempt 1: Fetch with Firecrawl (raw HTML)
        fc = self._get_firecrawl()
        if fc:
            try:
                result = fc.scrape(content_url, formats=['html'])
                html = result.get('html', '') if isinstance(result, dict) else getattr(result, 'html', '')
                html = html or ''
                servers, downloads, direct_urls = self._extract_from_html(html)
            except Exception:
                pass

        # Attempt 2: Fetch with Firecrawl + click action
        if not servers and not direct_urls and fc:
            try:
                result = fc.scrape(content_url, formats=['html'], actions=[
                    {"type": "click", "selector": ".watchNow button"},
                    {"type": "wait", "milliseconds": 500},
                ])
                html2 = result.get('html', '') if isinstance(result, dict) else getattr(result, 'html', '')
                html2 = html2 or ''
                if html2:
                    servers, downloads, direct_urls = self._extract_from_html(html2)
            except Exception:
                pass

        # Attempt 3: Firecrawl + click server tab
        if not servers and not direct_urls and fc:
            try:
                result = fc.scrape(content_url, formats=['html'], actions=[
                    {"type": "click", "selector": "ul.serversList li:first-child"},
                    {"type": "wait", "milliseconds": 800},
                ])
                html3 = result.get('html', '') if isinstance(result, dict) else getattr(result, 'html', '')
                html3 = html3 or ''
                if html3:
                    servers, downloads, direct_urls = self._extract_from_html(html3)
            except Exception:
                pass

        # Attempt 4: Submit the site's View=1 form. A normal GET only exposes
        # the trailer; the POST renders the actual watch/download servers.
        if not servers and not direct_urls:
            html = self._fetch_watch_page(content_url, timeout=15)
            if not html:
                _, html = self._fetch(content_url, timeout=15)
            if html:
                s2, d2, u2 = self._extract_from_html(html)
                if s2 or u2:
                    servers, downloads, direct_urls = s2, d2, u2

        ret = {
            'servers': servers,
            'downloads': downloads,
            'direct_urls': direct_urls[:3],
            'page_url': content_url
        }
        self._cache[cache_key] = ret
        return ret

    def _extract_from_html(self, html: str):
        """Extract servers, downloads, and direct URLs from HTML content."""
        servers = []
        downloads = []
        direct_urls = []

        if not html:
            return servers, downloads, direct_urls

        # 1. Parse Servers from "serversList"
        pattern = r'<li[^>]*data-link=["\']([^"\']+)["\'][^>]*>.*?<p>([^<]+)</p>'
        for match in re.finditer(pattern, html, re.DOTALL | re.IGNORECASE):
            url, name = match.groups()
            servers.append({'name': name.strip(), 'url': url.strip()})

        # 2. Extract Downloads from "donwload-servers-list"
        dl_block_match = re.search(
            r'<ul[^>]*class=["\'][^"\']*donwload-servers-list[^"\']*["\'][^>]*>(.*?)</ul>',
            html, re.DOTALL | re.IGNORECASE
        )
        if dl_block_match:
            for li_html in re.split(r'</li>', dl_block_match.group(1), flags=re.IGNORECASE):
                if not li_html.strip():
                    continue
                name_m = re.search(
                    r'<span[^>]*class=["\'][^"\']*ser-name[^"\']*["\'][^>]*>(.*?)</span>',
                    li_html, re.IGNORECASE | re.DOTALL
                )
                qual_m = re.search(
                    r'<div[^>]*class=["\'][^"\']*server-info[^"\']*["\'][^>]*>.*?<em[^>]*>(.*?)</em>',
                    li_html, re.IGNORECASE | re.DOTALL
                )
                url_m = re.search(r'<a[^>]*href=["\']([^"\']+)["\']', li_html, re.IGNORECASE)

                if qual_m and url_m:
                    name = name_m.group(1).strip() if name_m and name_m.group(1).strip() else "Direct Download"
                    downloads.append({
                        'name': name,
                        'quality': qual_m.group(1).strip(),
                        'url': url_m.group(1).strip()
                    })

        # Deduplicate downloads by URL
        seen_urls = set()
        unique_downloads = []
        for d in downloads:
            if d['url'] not in seen_urls:
                seen_urls.add(d['url'])
                unique_downloads.append(d)
        downloads = unique_downloads

        # 3. Fallback: Parse iframes
        if not servers:
            all_iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            embed_urls = [
                src for src in all_iframes
                if any(h in src.lower() for h in VIDEO_HOSTS)
                and not any(h in src.lower() for h in TRAILER_HOSTS)
                and 'recaptcha' not in src
                and 'facebook.com/plugins' not in src
            ]
            for i, url in enumerate(embed_urls[:5]):
                servers.append({'name': f'Server {i+1}', 'url': url})

        # 4. Sanitized iframe divs
        if not servers:
            sanitized = re.findall(
                r'<div[^>]+src=["\']([^"\']+)["\'][^>]+data-original-tag=["\']iframe["\']',
                html, re.IGNORECASE
            )
            if not sanitized:
                sanitized = re.findall(
                    r'<div[^>]+data-original-tag=["\']iframe["\'][^>]+src=["\']([^"\']+)["\']',
                    html, re.IGNORECASE
                )
            embed_urls = [
                src for src in sanitized
                if any(h in src.lower() for h in VIDEO_HOSTS)
                and not any(h in src.lower() for h in TRAILER_HOSTS)
                and 'recaptcha' not in src
            ]
            for i, url in enumerate(embed_urls[:5]):
                servers.append({'name': f'Server {i+1}', 'url': url})

        # 5. Direct video files
        direct_urls = list(dict.fromkeys(re.findall(
            r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*)',
            html
        )))

        # 6. data-src fallback
        if not servers and not direct_urls:
            ds = re.findall(r'data-src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            embed_urls = [
                u for u in ds
                if any(h in u.lower() for h in VIDEO_HOSTS)
                and not any(h in u.lower() for h in TRAILER_HOSTS)
            ]
            for i, url in enumerate(embed_urls[:5]):
                servers.append({'name': f'Server {i+1}', 'url': url})

        return servers, downloads, direct_urls

    # ------------------------------------------------------------------ #
    #  Utilities
    # ------------------------------------------------------------------ #

    @staticmethod
    def _classify_url(url: str) -> str:
        if '/episode/' in url: return 'episode'
        if '/season/' in url:  return 'season'
        if '/serie/' in url:   return 'series'
        if '/assembly/' in url: return 'collection'
        return 'movie'

    @staticmethod
    def _clean_title(title: str) -> str:
        title = title.strip()
        title = re.sub(
            r'^(مشاهدة\s+)?(فيلم|مسلسل|كرتون|سلسلة|جميع مواسم|كل مواسم)\s+',
            '', title
        )
        title = re.sub(
            r'\s+(مترجم|مدبلج|كامل|مترجمة)(\s+.*)?$',
            '', title
        )
        return title.strip()
