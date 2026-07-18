"""Royal-Drama scraper (Melody-template CMS).

Site structure:
  - Homepage : /home8
  - Series   : /all-series1.php
  - Movies   : /movies.php
  - Episodes : /episodes2.php
  - Watch    : /watch.php?vid=<9-char hex>
  - Search   : /search.php?keywords=...   (heavily bot-protected → best-effort)

Listing / watch pages are server-fetchable. The video player is loaded via
JavaScript, so a direct stream URL cannot be extracted server-side; the app
routes the watch URL through the generic /api/resolve-embed pipeline and also
offers the original site link as a fallback.
"""
import re
import requests as _req

BASE = "https://w9.royal-drama.com"
HOMEPAGE = "https://w9.royal-drama.com/home8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en;q=0.8",
    "Referer": HOMEPAGE + "/",
}

_CAT_URLS = {
    "turkish-series":  "https://w9.royal-drama.com/category3.php?cat=turkish-series-3sk",
    "arabic-series":   "https://w9.royal-drama.com/category3.php?cat=arabic-series1-2024",
    "indian-series":   "https://w9.royal-drama.com/category3.php?cat=indian-series-2025",
    "asian-series":    "https://w9.royal-drama.com/category3.php?cat=musalsalat-asiawia",
    "foreign-series":  "https://w9.royal-drama.com/category3.php?cat=musalsalat-ajnabia-netflix",
    "anime-series":    "https://w9.royal-drama.com/category3.php?cat=musalsalat-animiee-2025",
    "tv-shows":        "https://w9.royal-drama.com/category3.php?cat=tv-shows",
    "movies":          "https://w9.royal-drama.com/category3.php?cat=aflams-2026-1",
}


def _fetch(url: str, timeout: int = 30) -> str | None:
    try:
        r = _req.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.content.decode("utf-8", errors="replace")
    except Exception:
        return None


def _abs(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE + url
    return BASE + "/" + url


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def _parse_grid(html: str, force_type: str | None = None) -> list[dict]:
    """Parse the <li class="...col-..."> thumbnail cards used across listings."""
    items: list[dict] = []
    seen = set()
    for block in re.finditer(
        r'<li[^>]*class="[^"]*col-(?:xs|sm|md)-\d+[^"]*"[^>]*>(.*?)</li>',
        html, re.DOTALL,
    ):
        seg = block.group(1)
        a = re.search(r'<a[^>]*href="([^"]+)"[^>]*title="([^"]*)"', seg)
        if not a:
            a = re.search(r'<a[^>]*title="([^"]*)"[^>]*href="([^"]+)"', seg)
        if not a:
            continue
        href = _abs(a.group(1))
        name = _clean(a.group(2)) or _clean(re.search(r'title="([^"]+)"', seg).group(1) if re.search(r'title="([^"]+)"', seg) else "")
        if not name or "royal-drama.com" in name.lower():
            continue
        if href in seen:
            continue
        seen.add(href)

        poster_m = re.search(r'<img[^>]*src="([^"]+)"', seg)
        poster = _abs(poster_m.group(1)) if poster_m else ""
        dur_m = re.search(r'pm-label-duration">([^<]+)<', seg)
        duration = _clean(dur_m.group(1)) if dur_m else ""

        is_series = bool(re.search(r'الحلقة|مسلسل|series', name, re.IGNORECASE))
        ctype = force_type or ("series" if is_series else "movie")

        items.append({
            "name": name,
            "url": href,
            "poster": poster,
            "duration": duration,
            "type": ctype,
            "source": "royaldrama",
        })
    return items


def search(query: str) -> list[dict]:
    """Search is bot-protected server-side. Try cloudscraper first.
    If it fails, fall back to scanning the latest pages concurrently."""
    try:
        import cloudscraper
        sc = cloudscraper.create_scraper()
        r = sc.get(BASE + "/search.php", params={"keywords": query},
                   headers=HEADERS, timeout=10)
        if r.status_code == 200 and "pm-ul-browse-videos" in r.text:
            return _parse_grid(r.text)
    except Exception:
        pass

    # Best-effort fallback: search through recent pages
    import concurrent.futures
    results = []
    seen_urls = set()
    query_lower = query.lower()

    def fetch_and_filter(func, page):
        try:
            items = func(page)
            return [item for item in items if query_lower in item.get('name', '').lower()]
        except Exception:
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for p in range(1, 4):
            futures.append(executor.submit(fetch_and_filter, get_series, p))
            futures.append(executor.submit(fetch_and_filter, get_movies, p))
            futures.append(executor.submit(fetch_and_filter, get_episodes_list, p))

        for future in concurrent.futures.as_completed(futures):
            for item in future.result():
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    results.append(item)

    return results


def get_homepage() -> list[dict]:
    html = _fetch(HOMEPAGE)
    return _parse_grid(html) if html else []


def get_series(page: int = 1) -> list[dict]:
    url = "https://w9.royal-drama.com/all-series1.php"
    if page > 1:
        url = f"https://w9.royal-drama.com/all-series{page}.php"
    html = _fetch(url)
    return _parse_grid(html, force_type="series") if html else []


def get_movies(page: int = 1) -> list[dict]:
    url = "https://w9.royal-drama.com/movies.php"
    if page > 1:
        url = f"https://w9.royal-drama.com/movies{page}.php"
    html = _fetch(url)
    return _parse_grid(html, force_type="movie") if html else []


def get_episodes_list(page: int = 1) -> list[dict]:
    url = "https://w9.royal-drama.com/episodes2.php"
    if page > 1:
        url = f"https://w9.royal-drama.com/episodes{page}.php"
    html = _fetch(url)
    return _parse_grid(html, force_type="series") if html else []


def get_categories() -> list[dict]:
    return [{"slug": k, "name": k.replace("-", " ").title(), "type":
             "series" if "series" in k else "movie"} for k in _CAT_URLS]


def get_category_items(slug: str) -> list[dict]:
    url = _CAT_URLS.get(slug)
    if not url:
        return []
    html = _fetch(url)
    return _parse_grid(html) if html else []


def get_detail(url: str) -> dict:
    """Scrape a /watch.php?vid=… page for metadata + episodes + server link."""
    html = _fetch(url)
    if not html:
        return {"metadata": {}, "type": "movie", "episodes": [], "servers": []}

    # Title
    name = ""
    h1 = re.search(r"<h1[^>]*itemprop=\"name\"[^>]*>(.*?)</h1>", html, re.DOTALL)
    if h1:
        name = _clean(h1.group(1))
    if not name:
        og = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', html)
        if og:
            name = _clean(og.group(1))

    # Poster
    poster = ""
    og_img = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
    if og_img:
        poster = _abs(og_img.group(1))
    if not poster:
        thumb = re.search(r'<meta[^>]*itemprop="thumbnailUrl"[^>]*content="([^"]+)"', html)
        if thumb:
            poster = _abs(thumb.group(1))

    # Duration
    duration = ""
    dur = re.search(r'<meta[^>]*itemprop="duration"[^>]*content="([^"]+)"', html)
    if dur:
        duration = _clean(dur.group(1))

    # Episodes (series page lists them in #SeasonN tabcontent blocks)
    episodes: list[dict] = []
    seen = set()
    for block in re.finditer(r'<div id="Season\d+"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL):
        for a in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*title="([^"]*)"', block.group(1)):
            href = _abs(a.group(1))
            if "watch.php?vid=" not in href or href in seen:
                continue
            seen.add(href)
            episodes.append({
                "name": _clean(a.group(2)) or "Episode",
                "url": href,
            })

    ctype = "series" if episodes else "movie"

    # Server entry = the watch page itself, routed through /api/resolve-embed.
    servers = []
    view_url = url.replace("watch.php", "view.php")
    try:
        v_html = _fetch(view_url)
        for li_match in re.finditer(r'<li[^>]*data-embed="([^"]+)"[^>]*>(.*?)</li>', v_html, re.IGNORECASE | re.DOTALL):
            embed_html = li_match.group(1)
            inner_html = li_match.group(2)
            
            src_match = re.search(r"src=['\"]([^'\"]+)['\"]", embed_html, re.IGNORECASE)
            name_match = re.search(r"<strong>([^<]+)</strong>", inner_html, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r">([^<]+)</a>", inner_html, re.IGNORECASE)
                
            if src_match and name_match:
                servers.append({"name": name_match.group(1).strip(), "url": src_match.group(1)})
                
        # If no servers found from li tags, try finding an iframe directly in view_url
        if not servers and v_html:
            iframe_match = re.search(r'<iframe[^>]*src=["\']([^"\']+)["\']', v_html, re.IGNORECASE)
            if iframe_match:
                servers.append({"name": "Server 1", "url": iframe_match.group(1)})
                
    except Exception as e:
        pass
    
    if not servers:
        # Try finding an iframe directly in watch url
        iframe_match = re.search(r'<iframe[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if iframe_match:
            servers.append({"name": "Server 1", "url": iframe_match.group(1)})

    return {
        "metadata": {
            "name": name,
            "poster": poster,
            "duration": duration,
            "type": ctype,
        },
        "type": ctype,
        "episodes": episodes,
        "servers": servers,
    }
