"""Server-side Sahid4u API.

Since sahid4u.com search endpoint is behind Cloudflare + LiteSpeed,
we use multiple strategies:
  1. Primary: cloudscraper + curl_cffi for pages that allow it
  2. Fallback: Firecrawl API (same as EgyDead) for search
  3. Category/homepage scraping for discovery
"""

import re, json, os
from urllib.parse import unquote

FALLBACK_DOMAIN = "https://shhahhid4u.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

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
            if r.status_code == 200:
                return r.text
            last_error = f'{name}: HTTP {r.status_code}'
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
    q_encoded = query.replace(' ', '+')

    # Strategy 1: Firecrawl API (handles Cloudflare)
    try:
        from firecrawl import Firecrawl
        api_key = os.environ.get('FIRECRAWL_API_KEY')
        if not api_key:
            raise RuntimeError('FIRECRAWL_API_KEY is not configured')
        fc = Firecrawl(api_key=api_key)
        for url in [
            f'{FALLBACK_DOMAIN}/?s={q_encoded}',
            f'{FALLBACK_DOMAIN}/category-search-api-v2?q={q_encoded}',
        ]:
            try:
                result = fc.scrape(url, formats=['html'])
                html = result.get('html', '') if isinstance(result, dict) else getattr(result, 'html', '') or ''
                if html:
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
            f'{FALLBACK_DOMAIN}/?s={q_encoded}',
            impersonate='chrome120',
            headers=HEADERS,
            timeout=15
        )
        if r.status_code == 200:
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
                    response = page.goto(f'{FALLBACK_DOMAIN}/?s={q_encoded}', wait_until='domcontentloaded', timeout=20000)
                    page.wait_for_timeout(3000)
                    html = page.content()
                    if response and response.ok and 'Just a moment' not in html:
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
        watch_url = f'{FALLBACK_DOMAIN}/watch/{slug}'

    try:
        html = _fetch(watch_url, timeout=12)
    except Exception:
        return []

    # rawServers JSON
    m = re.search(r'let\s+rawServers\s*=\s*(\[[\s\S]*?\])\s*;', html, re.IGNORECASE)
    if m:
        try:
            servers = json.loads(m.group(1))
            return [{
                'name': s.get('name', f'Server {i+1}'),
                'url': s.get('url', ''),
                'id': s.get('id'),
            } for i, s in enumerate(servers)]
        except json.JSONDecodeError:
            pass

    # iframe fallback
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if iframes:
        return [{'name': 'Embed', 'url': iframes[0]}]

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

    return {
        'title': title,
        'watch_url': f'{FALLBACK_DOMAIN}/watch/{slug}' if slug else None,
        'download_url': f'{FALLBACK_DOMAIN}/download/{slug}' if slug else None,
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
        watch_url = f'{FALLBACK_DOMAIN}/watch/{slug}'
        download_url = f'{FALLBACK_DOMAIN}/download/{slug}'

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
            html = _fetch(watch_url, timeout=12)
            if html:
                raw_servers = None
                m = re.search(r'let\s+rawServers\s*=\s*(\[[\s\S]*?\])\s*;', html, re.IGNORECASE)
                if m:
                    try:
                        raw_servers = json.loads(m.group(1))
                    except json.JSONDecodeError:
                        pass
                if raw_servers is None:
                    nested = re.search(
                        r'''let\s+servers\s*=\s*JSON\.parse\(\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)')\s*\)\s*;''',
                        html, re.IGNORECASE
                    )
                    if nested:
                        try:
                            payload = nested.group(1)
                            if payload is not None:
                                payload = json.loads(f'"{payload}"')
                            else:
                                payload = nested.group(2).replace("\\'", "'")
                            raw_servers = json.loads(payload)
                        except (json.JSONDecodeError, TypeError):
                            pass
                if isinstance(raw_servers, list):
                    servers = [{
                        'name': s.get('name', f'Server {i+1}'),
                        'url': s.get('url', ''),
                        'id': s.get('id'),
                    } for i, s in enumerate(raw_servers) if isinstance(s, dict)]
                if not servers:
                    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
                    if iframes:
                        servers = [{'name': 'Embed', 'url': iframes[0]}]
        except Exception:
            pass

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
