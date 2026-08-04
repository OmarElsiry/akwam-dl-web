"""Server-side Sahid4u API.

Since sahid4u.com search endpoint is behind Cloudflare + LiteSpeed,
we use multiple strategies:
  1. Primary: cloudscraper + curl_cffi for pages that allow it
  2. Fallback: Firecrawl API (same as EgyDead) for search
  3. Category/homepage scraping for discovery
"""

import re, json, os
from urllib.parse import quote_plus, urlsplit, urlunsplit

FALLBACK_DOMAIN = "https://shhahhid4u.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def _is_challenge_page(html):
    """Distinguish a blocking Cloudflare page from its injected telemetry script.

    Cloudflare appends ``challenge-platform/scripts/jsd`` to successful pages
    too, so that script path by itself is not evidence that access is blocked.
    """
    return bool(re.search(
        r'<title[^>]*>\s*(?:Just a moment|Attention Required)|'
        r'id=["\']cf-error-details["\']|'
        r'class=["\'][^"\']*(?:cf-turnstile|challenge-form)[^"\']*["\']|'
        r'id=["\']challenge-(?:form|stage|running)["\']',
        html or '', re.IGNORECASE
    ))


# Try multiple fetch strategies
def _fetch(url, timeout=15):
    strategies = []

    # Strategy 1: cloudscraper
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        strategies.append(('cloudscraper', lambda: scraper.get(url, headers=HEADERS, timeout=timeout)))
    except ImportError:
        pass

    # Strategy 2: curl_cffi with Chrome impersonation
    try:
        from curl_cffi import requests as curl_req
        strategies.append(('curl_cffi', lambda: curl_req.get(url, impersonate='chrome120', headers=HEADERS, timeout=timeout)))
    except ImportError:
        pass

    # Strategy 3: plain requests
    import requests
    strategies.append(('requests', lambda: requests.get(url, headers=HEADERS, timeout=timeout)))

    last_error = None
    for name, fn in strategies:
        try:
            r = fn()
            if r.status_code == 200 and not _is_challenge_page(r.text):
                return r.text
            suffix = ' provider challenge' if _is_challenge_page(r.text) else ''
            last_error = f'{name}: HTTP {r.status_code}{suffix}'
        except Exception as e:
            last_error = f'{name}: {type(e).__name__}: {str(e)[:80]}'

    # Strategy 4: Firecrawl (if available)
    try:
        from firecrawl import Firecrawl
        api_key = os.environ.get('FIRECRAWL_API_KEY')
        if not api_key:
            raise RuntimeError('FIRECRAWL_API_KEY is not configured')
        fc = Firecrawl(api_key=api_key)
        result = fc.scrape(url, formats=['markdown', 'html'])
        if result:
            md = getattr(result, 'markdown', '') or ''
            html = (result.get('html', '') if isinstance(result, dict) else getattr(result, 'html', '')) or ''
            return html or md
    except Exception:
        pass

    raise RuntimeError(f'All fetch strategies failed for {url}: {last_error}')


def _extract_links(html, base_url=FALLBACK_DOMAIN):
    """Extract all <a> links with names from HTML."""
    links = []
    for m in re.finditer(r'<a[^>]*href=(["\'])([^"\']+)\1[^>]*>([\s\S]*?)</a>', html, re.DOTALL | re.IGNORECASE):
        href = m.group(2).strip()
        inner = m.group(3)
        if href.startswith('/'):
            href = base_url + href
        if not href.startswith('http'):
            continue
        name = _extract_name(inner, href)
        links.append({'href': href, 'name': name})
    return links


def _extract_name(inner, href):
    name_m = re.search(r'<p[^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>([\s\S]*?)</p>', inner, re.IGNORECASE)
    if name_m:
        return re.sub(r'<[^>]+>', '', name_m.group(1)).strip()
    h_m = re.search(r'<(h[23])[^>]*>([\s\S]*?)</\1>', inner, re.IGNORECASE)
    if h_m:
        return re.sub(r'<[^>]+>', '', h_m.group(2)).strip()
    img_alt = re.search(r'alt=(["\'])([^"\']+)\1', inner, re.IGNORECASE)
    if img_alt:
        return img_alt.group(2)
    return href.split('/').pop().replace('-', ' ').replace('_', ' ').title()


def search(query):
    """Search sahid4u for content.

    The /search endpoint is behind Cloudflare + LiteSpeed WAF, so we use:
    1. Firecrawl API (same as EgyDead)
    2. curl_cffi with Chrome impersonation (handles some Cloudflare setups)
    3. Direct URL-based discovery methods
    """
    ql = query.lower()
    seen = set()
    results = []
    source_reached = False
    q_encoded = quote_plus(query)

    # Strategy 1: Firecrawl API (handles Cloudflare)
    try:
        from firecrawl import Firecrawl
        api_key = os.environ.get('FIRECRAWL_API_KEY')
        if not api_key:
            raise RuntimeError('FIRECRAWL_API_KEY is not configured')
        fc = Firecrawl(api_key=api_key)
        for url in [
            f'{FALLBACK_DOMAIN}/search?s={q_encoded}',
            f'{FALLBACK_DOMAIN}/category-search-api-v2?q={q_encoded}',
        ]:
            try:
                result = fc.scrape(url, formats=['html'])
                html = result.get('html', '') if isinstance(result, dict) else getattr(result, 'html', '') or ''
                if html and not _is_challenge_page(html):
                    source_reached = True
                    links = _extract_links(html)
                    for link in links:
                        href = link['href']
                        name = link['name']
                        if href in seen or ql not in name.lower():
                            continue
                        ctype = _detect_type(href)
                        if not ctype:
                            continue
                        seen.add(href)
                        results.append({'name': name, 'url': href, 'type': ctype, 'source': 'sahid4u'})
                    if results:
                        return results
            except Exception:
                continue
    except Exception:
        pass

    # Strategy 2: curl_cffi with Chrome impersonation (handles some Cloudflare)
    try:
        from curl_cffi import requests as curl_req
        r = curl_req.get(
            f'{FALLBACK_DOMAIN}/search?s={q_encoded}',
            impersonate='chrome120',
            headers=HEADERS,
            timeout=15
        )
        if r.status_code == 200 and not _is_challenge_page(r.text):
            source_reached = True
            html = r.text
            links = _extract_links(html)
            for link in links:
                href = link['href']
                name = link['name']
                if href in seen or ql not in name.lower():
                    continue
                ctype = _detect_type(href)
                if not ctype:
                    continue
                seen.add(href)
                results.append({'name': name, 'url': href, 'type': ctype, 'source': 'sahid4u'})
            if results:
                return results
    except Exception:
        pass

    # Strategy 3: Playwright headless browser (slow but handles JS sites)
    if not results:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()
                try:
                    response = page.goto(f'{FALLBACK_DOMAIN}/search?s={q_encoded}', wait_until='domcontentloaded', timeout=20000)
                    page.wait_for_timeout(3000)
                    html = page.content()
                    if response and response.ok and not _is_challenge_page(html):
                        source_reached = True
                except Exception:
                    html = ''
                browser.close()

                if html:
                    links = _extract_links(html)
                    for link in links:
                        href = link['href']
                        name = link['name']
                        if href in seen or ql not in name.lower():
                            continue
                        ctype = _detect_type(href)
                        if not ctype:
                            continue
                        seen.add(href)
                        results.append({'name': name, 'url': href, 'type': ctype, 'source': 'sahid4u'})
        except Exception:
            pass

    if not source_reached:
        raise RuntimeError('Sahid4u is currently blocking automated access')
    return results


def _detect_type(href):
    if '/film/' in href: return 'movie'
    if '/series/' in href: return 'series'
    if '/episode/' in href: return 'episode'
    return None


def _related_url(content_url, route, slug):
    """Build a related provider URL without switching the content's host."""
    parsed = urlsplit(content_url)
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.netloc, f'/{route}/{slug}', '', ''))
    return f'{FALLBACK_DOMAIN}/{route}/{slug}'


def _session_with_watch_page(watch_url, timeout=12):
    """Fetch the /watch/ page with a real HTTP session so the cookies set by
    the site are available for the follow-up JSON POSTs. Returns a
    (session, html) tuple; ``html`` is guaranteed non-empty on success."""
    from curl_cffi import requests as creq
    s = creq.Session()
    r = s.get(
        watch_url,
        impersonate='chrome120',
        headers=HEADERS,
        timeout=timeout,
        allow_redirects=True,
    )
    if r.status_code != 200:
        raise RuntimeError(f'sahid4u watch HTTP {r.status_code}')
    html = r.text
    if _is_challenge_page(html):
        raise RuntimeError('sahid4u watch page is behind challenge')
    return s, html


def _parse_server_key_names(html):
    """Extract ordered (server_key, display_name) pairs from the /watch/ page."""
    pairs = []
    seen = set()
    for m in re.finditer(r'data-server-key="([a-f0-9]{8,64})"', html):
        key = m.group(1)
        if key in seen:
            continue
        seen.add(key)
        # Name lives in an <img title="..."> near the button.
        window = html[max(0, m.start()-600):m.start()+600]
        titles = re.findall(r'title="([^"<]{1,64})"', window)
        name = titles[-1] if titles else f'Server {len(pairs) + 1}'
        pairs.append({'key': key, 'name': name})
    return pairs


def _issue_player_url(session, watch_url, html, server_key, timeout=12):
    """POST /secure-watch/issue for one server key and return its player_url."""
    page_token_m = re.search(r'pageToken\s*=\s*"([^"]+)"', html)
    csrf_m = re.search(r'csrfToken\s*=\s*"([^"]+)"', html)
    issue_m = re.search(r'issueUrl\s*=\s*"([^"]+)"', html)
    if not (page_token_m and csrf_m):
        return None, 'missing pageToken/csrfToken'
    page_token = page_token_m.group(1)
    csrf = csrf_m.group(1)
    if issue_m:
        issue_url = issue_m.group(1).replace('\\/', '/')
    else:
        p = urlsplit(watch_url)
        issue_url = urlunsplit((p.scheme, p.netloc, '/secure-watch/issue', '', ''))
    # curl_cffi headers are latin-1; quote the Arabic path before sending.
    from urllib.parse import quote as _q
    safe_referer = _q(watch_url, safe=':/?#[]@!$&\'()*+,;=%')
    resp = session.post(
        issue_url,
        json={'page_token': page_token, 'server_key': server_key},
        headers={
            **HEADERS,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRF-TOKEN': csrf,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': safe_referer,
            'Origin': f'{urlsplit(watch_url).scheme}://{urlsplit(watch_url).netloc}',
        },
        timeout=timeout,
        impersonate='chrome120',
    )
    if resp.status_code != 200:
        return None, f'HTTP {resp.status_code}'
    data = resp.json()
    player_url = data.get('player_url') or data.get('url')
    if not player_url:
        return None, 'no player_url'
    return player_url, None


def get_content_servers(content_url):
    """Extract watch servers from a Sahid4u page.

    Accepts /film/{slug}, /episode/{slug}, or /watch/{slug} URLs.
    """
    # Extract slug from URL (handles /film/, /episode/, /watch/)
    slug_m = re.search(r'/(?:film|episode|watch)/([^/?#]+)', content_url)
    if not slug_m:
        return []
    slug = slug_m.group(1)
    # If it's already a /watch/ URL, use it directly
    if '/watch/' in content_url:
        watch_url = content_url.rstrip('/')
    else:
        watch_url = _related_url(content_url, 'watch', slug)

    # Try the legacy mock-friendly fetch first: rawServers JSON or a plain
    # iframe on a pre-2026 page. Real pages 404 this path today, but keeping
    # it cheap preserves the regression harness and any old-mirror traffic.
    try:
        legacy_html = _fetch(watch_url, timeout=12)
    except Exception:
        legacy_html = ''

    m = re.search(r'let\s+rawServers\s*=\s*(\[[\s\S]*?\])\s*;', legacy_html or '', re.IGNORECASE)
    if m:
        try:
            raw = json.loads(m.group(1))
            return [{
                'name': s.get('name', f'Server {i+1}'),
                'url': s.get('url', ''),
                'id': s.get('id'),
            } for i, s in enumerate(raw)]
        except json.JSONDecodeError:
            pass

    legacy_iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', legacy_html or '', re.IGNORECASE)
    if legacy_iframes:
        return [{'name': 'Embed', 'url': legacy_iframes[0]}]

    # New flow: /watch/ page ships server keys + CSRF; each embed is only
    # revealed via POST /secure-watch/issue with a session cookie.
    try:
        session, html = _session_with_watch_page(watch_url)
    except Exception:
        html = ''

    keys = _parse_server_key_names(html) if html else []
    issued = []
    for info in keys or []:
        player_url, _err = _issue_player_url(session, watch_url, html, info['key'])
        if player_url:
            issued.append({
                'name': info['name'],
                'url': player_url,
                'key': info['key'],
                'embed_url': player_url,
            })
    if issued:
        return issued

    # POST-to-issue flow is TLS-fingerprint gated; curl_cffi gets 404s while
    # real Chromium passes. Hand the UI the watch page so the player resolver
    # drives a real browser click through /api/resolve-embed.
    # ponytail: when issue POST works server-side again, delete this branch.
    if keys:
        return [{
            'name': 'سيرفر المشاهدة (Sahid4u Play)',
            'url': watch_url,
            'embed_url': watch_url,
        }]
    return []


def get_content_info(content_url):
    """Get title, watch URL, and download URL from a content page."""
    try:
        html = _fetch(content_url, timeout=12)
    except Exception:
        return {'title': '', 'watch_url': None, 'download_url': None}

    title = ''
    title_m = re.search(r'<title>([^<]*)</title>', html)
    if title_m:
        title = title_m.group(1).strip()

    slug_m = re.search(r'/(?:film|episode)/([^/?#]+)', content_url)
    slug = slug_m.group(1) if slug_m else ''

    links = _extract_links(html, f'{urlsplit(content_url).scheme}://{urlsplit(content_url).netloc}')
    watch_links = [link['href'] for link in links if '/watch/' in link['href']]
    download_links = [link['href'] for link in links if '/download/' in link['href']]

    return {
        'title': title,
        'watch_url': watch_links[0] if watch_links else (_related_url(content_url, 'watch', slug) if slug else None),
        'download_url': download_links[0] if download_links else (_related_url(content_url, 'download', slug) if slug else None),
    }


def get_seasons(series_url):
    """Extract season links from a series page."""
    try:
        html = _fetch(series_url, timeout=12)
    except Exception:
        return []
    links = _extract_links(html)
    seen = set()
    seasons = []
    for link in links:
        if '/season/' not in link['href']:
            continue
        if link['href'] in seen:
            continue
        seen.add(link['href'])
        seasons.append({'name': link['name'] or 'Season', 'url': link['href']})
    return seasons


def get_episodes(season_url):
    """Extract episode links from a season page."""
    try:
        html = _fetch(season_url, timeout=12)
    except Exception:
        return []
    links = _extract_links(html)
    seen = set()
    episodes = []
    for link in links:
        if '/episode/' not in link['href']:
            continue
        if link['href'] in seen:
            continue
        seen.add(link['href'])
        episodes.append({'name': link['name'] or 'Episode', 'url': link['href']})
    return episodes


def get_content_servers_and_downloads(content_url):
    """Get all servers + download info for a film/episode page."""
    slug_m = re.search(r'/(?:film|episode)/([^/?#]+)', content_url)
    watch_url = None
    download_url = None
    if slug_m:
        slug = slug_m.group(1)
        watch_url = _related_url(content_url, 'watch', slug)
        download_url = _related_url(content_url, 'download', slug)

    try:
        info = get_content_info(content_url)
    except Exception:
        info = {}
    if info.get('watch_url'):
        watch_url = info['watch_url']
    if info.get('download_url'):
        download_url = info['download_url']

    servers = []
    qualities = []
    if watch_url:
        try:
            servers = get_content_servers(watch_url)
        except Exception:
            servers = []

    if download_url:
        try:
            html = _fetch(download_url, timeout=12)
            if html:
                for m in re.finditer(
                    r'<a[^>]*href=["\']/quality/([^"\']+)["\'][^>]*class=["\'][^"\']*btn-gray[^"\']*["\'][^>]*>([\s\S]*?)</a>',
                    html, re.IGNORECASE
                ):
                    name = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                    if name:
                        qualities.append(name)
        except Exception:
            pass

    return {'servers': servers, 'qualities': qualities, 'watch_url': watch_url, 'download_url': download_url}


def get_episode_series_info(episode_url):
    """Extract series and season links from an episode page for back-navigation."""
    try:
        html = _fetch(episode_url, timeout=12)
    except Exception:
        return {'series': None, 'season': None}
    links = _extract_links(html)
    series_links = [l for l in links if '/series/' in l['href']]
    season_links = [l for l in links if '/season/' in l['href']]
    return {
        'series': {'name': series_links[0]['name'], 'url': series_links[0]['href']} if series_links else None,
        'season': {'name': season_links[0]['name'], 'url': season_links[0]['href']} if season_links else None,
    }
