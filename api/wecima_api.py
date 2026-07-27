import re, json, base64
import requests as _req

BASE = "https://wecima.cx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": BASE + "/",
    "Origin": BASE,
}


def _decode_url(data: str) -> str | None:
    """Decode Wecima's base64-encoded URL."""
    if not data:
        return None
    try:
        # Try standard pattern first: "aHR0c" + data
        cleaned = data.replace("+", "")
        full = "aHR0c" + cleaned
        return base64.b64decode(full).decode("utf-8")
    except Exception:
        pass
    try:
        # Try direct base64 decode (data may include full protocol)
        return base64.b64decode(data).decode("utf-8")
    except Exception:
        pass
    try:
        # Try prepending "aHR0cDovL" (http://) or "aHR0cHM6Ly8" (https://)
        for prefix in ["aHR0cHM6Ly8", "aHR0cDovLw"]:
            try:
                return base64.b64decode(prefix + cleaned).decode("utf-8")
            except Exception:
                continue
    except Exception:
        pass
    return None


def _fetch(url: str, **kw) -> str | None:
    kw.setdefault("headers", HEADERS)
    kw.setdefault("timeout", 30)
    try:
        r = _req.get(url, **kw)
        r.raise_for_status()
        return r.content.decode("utf-8", errors="replace")
    except Exception:
        return None


def _post_json(url: str, data: dict) -> dict | None:
    h = {**HEADERS, "Content-Type": "application/json",
         "X-Requested-With": "XMLHttpRequest"}
    try:
        r = _req.post(url, json=data, headers=h, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _post_form(url: str, form: dict) -> str | None:
    h = {**HEADERS, "Content-Type": "application/x-www-form-urlencoded",
         "X-Requested-With": "XMLHttpRequest"}
    try:
        r = _req.post(url, data=form, headers=h, timeout=30)
        r.raise_for_status()
        return r.content.decode("utf-8", errors="replace")
    except Exception:
        return None


# ──────────────────────────────────────────────
#  Search
# ──────────────────────────────────────────────

def search(query: str) -> list[dict]:
    """AJAX search — POST /search  (q=…)  → JSON."""
    raw = _post_form(BASE + "/search", {"q": query})
    if not raw:
        return _search_fallback(query)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _search_fallback(query)

    results = []
    for item in payload.get("results", []):
        istv = item.get("istv", 0)  # 0=movie (/watch/), 1=series (/series/)
        slug = item.get("slug", "")
        results.append({
            "name": item.get("title", ""),
            "url": f"{BASE}/{'watch' if istv == 0 else 'series'}/{slug}",
            "slug": slug,
            "year": str(item.get("year", "")).strip("()"),
            "poster": item.get("image", item.get("poster", "")),
            "type": "movie" if istv == 0 else "series",
            "source": "wecima",
        })
    return results


def _search_fallback(query: str) -> list[dict]:
    """Fallback: scrape ?s= page."""
    html = _fetch(f"{BASE}/?s={query.replace(' ', '+')}")
    if not html:
        return []
    return _parse_grid_items(html)


# ──────────────────────────────────────────────
#  Homepage / Category listing
# ──────────────────────────────────────────────

CATEGORIES = [
    {"slug": "foreign-movies",      "name": "Foreign Movies",      "type": "movie"},
    {"slug": "arabic-movies",       "name": "Arabic Movies",       "type": "movie"},
    {"slug": "indian-movies",       "name": "Indian Movies",       "type": "movie"},
    {"slug": "asian-movies",        "name": "Asian Movies",        "type": "movie"},
    {"slug": "turkish-movies",      "name": "Turkish Movies",      "type": "movie"},
    {"slug": "anime-movies",        "name": "Anime Movies",        "type": "movie"},
    {"slug": "dubbed-movies",       "name": "Dubbed Movies",       "type": "movie"},
    {"slug": "foreign-series",      "name": "Foreign Series",      "type": "series"},
    {"slug": "arabic-series",       "name": "Arabic Series",       "type": "series"},
    {"slug": "indian-series",       "name": "Indian Series",       "type": "series"},
    {"slug": "asian-series",        "name": "Asian Series",        "type": "series"},
    {"slug": "turkish-series",      "name": "Turkish Series",      "type": "series"},
    {"slug": "anime-series",        "name": "Anime Series",        "type": "series"},
    {"slug": "tv-shows",            "name": "TV Shows",            "type": "series"},
    {"slug": "wwe-shows",           "name": "WWE Shows",           "type": "series"},
    {"slug": "ramadan-series-2026", "name": "Ramadan Series 2026", "type": "series"},
    {"slug": "ramadan-series-2025", "name": "Ramadan Series 2025", "type": "series"},
    {"slug": "ramadan-series-2024", "name": "Ramadan Series 2024", "type": "series"},
]


def get_categories() -> list[dict]:
    return CATEGORIES


def get_category_items(slug: str, page: int = 1) -> list[dict]:
    """Browse a category (paginated)."""
    if page <= 1:
        url = f"{BASE}/category/{slug}/"
    else:
        url = f"{BASE}/category/{slug}/page/{page}/"
    html = _fetch(url)
    if not html:
        return []
    return _parse_grid_items(html)


def get_homepage_tab(tab: str = "new") -> list[dict]:
    """Homepage tabs: 'new' (default), 'movies', 'series', 'episodes'."""
    urls = {
        "new":      BASE + "/",
        "movies":   BASE + "/movies",
        "series":   BASE + "/seriestv",
        "episodes": BASE + "/seriestv/episodes",
    }
    html = _fetch(urls.get(tab, BASE + "/"))
    if not html:
        return []
    return _parse_grid_items(html)


def _parse_grid_items(html: str) -> list[dict]:
    """Parse <div class='GridItem'> cards."""
    items = []
    # Each GridItem is a nested div structure; find them by matching the opening
    # <div class="GridItem"…> through to its closing </div> (depth tracking).
    pos = 0
    while True:
        start = html.find('<div class="GridItem"', pos)
        if start < 0:
            break
        depth = 1
        p = start + 22
        while depth > 0 and p < len(html):
            if html[p:p+4] == "<div" and html[p+1:p+2] != "/":
                depth += 1
                p += 4
            elif html[p:p+6] == "</div>":
                depth -= 1
                p += 6
            else:
                p += 1
        block = html[start:p]
        pos = p

        # Link
        link_m = re.search(r'<a[^>]*href="([^"]+)"', block)
        if not link_m:
            continue
        href = link_m.group(1)
        if not href.startswith("http"):
            href = BASE + href

        # Title from h2
        title_m = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.DOTALL)
        name = ""
        if title_m:
            raw = title_m.group(1)
            # Remove <span class="year"> tags entirely (including content)
            raw = re.sub(r'<span[^>]*class="year"[^>]*>.*?</span>', "", raw)
            name = re.sub(r'<[^>]+>', "", raw).strip()

        # Poster (lazy-loaded via data-src)
        poster = ""
        poster_m = re.search(r'data-src="([^"]+)"', block)
        if poster_m:
            poster = poster_m.group(1)
        if not poster:
            poster_m = re.search(r'data-lazy-src="([^"]+)"', block)
            if poster_m:
                poster = poster_m.group(1)
        if not poster:
            poster_m = re.search(r'<meta[^>]*itemprop="thumbnailUrl"[^>]*content="([^"]+)"', block)
            if poster_m:
                poster = poster_m.group(1)

        # Year
        year_m = re.search(r'<span class="year">\(?(\d{4})\)?</span>', block)
        year = year_m.group(1) if year_m else ""

        # Type
        ctype = "series" if "/series/" in href else "movie"

        if name:
            items.append({
                "name": name,
                "url": href,
                "poster": poster,
                "year": year,
                "type": ctype,
                "source": "wecima",
            })
    return items


# ──────────────────────────────────────────────
#  Watch page — Servers & Downloads
# ──────────────────────────────────────────────

def get_content_detail(url: str) -> dict:
    """Scrape a /watch/… page for servers + downloads + metadata."""
    html = _fetch(url)
    if not html:
        return {"metadata": {}, "servers": [], "downloads": []}

    metadata = _extract_metadata(html)
    servers = _extract_servers(html)
    downloads = _extract_downloads(html)

    return {"metadata": metadata, "servers": servers, "downloads": downloads}


def _extract_metadata(html: str) -> dict:
    meta = {}

    # JSON-LD
    ld_m = re.search(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if ld_m:
        try:
            ld = json.loads(ld_m.group(1))
        except json.JSONDecodeError:
            ld = {}
        if isinstance(ld, dict) and isinstance(ld.get("@graph"), list):
            # Wecima wraps the useful Movie/TVSeries schema in @graph.  Prefer
            # the entry carrying media metadata instead of the outer WebPage.
            candidates = [x for x in ld["@graph"] if isinstance(x, dict)]
            ld = next(
                (x for x in candidates if x.get("@type") in (
                    "Movie", "TVSeries", "TVEpisode", "VideoObject"
                )),
                next((x for x in candidates if x.get("numberOfEpisodes")), {}),
            )
        if isinstance(ld, dict):
            meta["name"] = ld.get("name", "")
            meta["description"] = ld.get("description", "")
            meta["duration"] = ld.get("duration", "")
            meta["datePublished"] = ld.get("datePublished", "")
            meta["numberOfSeasons"] = ld.get("numberOfSeasons")
            meta["numberOfEpisodes"] = ld.get("numberOfEpisodes")
            rating = ld.get("aggregateRating", {}) or {}
            if isinstance(rating, dict):
                meta["rating"] = rating.get("ratingValue", "")
                meta["ratingCount"] = rating.get("ratingCount", "")
            meta["image"] = ld.get("thumbnailUrl", "") or ld.get("image", "")
        elif isinstance(ld, list):
            for entry in ld:
                if isinstance(entry, dict) and entry.get("name"):
                    meta["name"] = entry.get("name", "")
                    meta["description"] = entry.get("description", "")
                    meta["duration"] = entry.get("duration", "")
                    break

    # <h1> fallback
    if not meta.get("name"):
        h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', html)
        if h1_m:
            meta["name"] = h1_m.group(1).strip()

    return meta


# Preferred server order for Wecima: try 3, then 4, then 1, then 2.
SERVER_PRIORITY = {3: 0, 4: 1, 1: 2, 2: 3}


def _reorder_servers(servers: list[dict]) -> list[dict]:
    """Reorder servers by SERVER_PRIORITY (unrecognized keep original order)."""
    def rank(s: dict, idx: int) -> tuple[int, int]:
        m = re.search(r"Server\s*(\d+)", s.get("name", ""), re.IGNORECASE)
        num = int(m.group(1)) if m else None
        return (SERVER_PRIORITY.get(num, 99), idx)
    return [s for _, s in sorted(enumerate(servers), key=lambda t: rank(t[1], t[0]))]


def _extract_servers(html: str) -> list[dict]:
    """Extract streaming servers using multiple fallback patterns."""
    servers = []

    # ── Pattern 1: <btn data-xpage data-url class="hoverable activable"> <strong> ──
    for m in re.finditer(
        r'<btn[^>]*data-xpage="([^"]+)"[^>]*data-url="([^"]+)"[^>]*'
        r'class="hoverable activable"[^>]*>.*?<strong>(.*?)</strong>',
        html, re.DOTALL
    ):
        url = _decode_url(m.group(2))
        if url:
            servers.append({
                "name": m.group(3).strip(),
                "url": url,
                "xpage": m.group(1),
            })

    # ── Pattern 2: Any element with data-xpage + data-url + class containing 'hoverable' ──
    if not servers:
        for m in re.finditer(
            r'<(\w+)[^>]*data-xpage="([^"]+)"[^>]*data-url="([^"]+)"[^>]*'
            r'class="[^"]*hoverable[^"]*"[^>]*>.*?<strong>(.*?)</strong>',
            html, re.DOTALL
        ):
            url = _decode_url(m.group(3))
            if url:
                servers.append({
                    "name": m.group(4).strip(),
                    "url": url,
                    "xpage": m.group(2),
                })

    # ── Pattern 3: data-xpage + data-url without strong tag ──
    if not servers:
        for m in re.finditer(
            r'data-xpage="([^"]+)"[^>]*data-url="([^"]+)"',
            html
        ):
            url = _decode_url(m.group(2))
            if url:
                servers.append({
                    "name": f"Server {len(servers) + 1}",
                    "url": url,
                    "xpage": m.group(1),
                })

    # ── Pattern 4: Any element with data-url attribute that base64 decodes ──
    if not servers:
        for m in re.finditer(
            r'data-url=["\']([a-zA-Z0-9+/=]+)["\']',
            html
        ):
            url = _decode_url(m.group(1))
            if url and url.startswith('http') and 'wecima' not in url:
                servers.append({
                    "name": f"Server {len(servers) + 1}",
                    "url": url,
                })

    # ── Pattern 5: data-href attribute ──
    if not servers:
        for m in re.finditer(
            r'data-href=["\']([a-zA-Z0-9+/=]+)["\']',
            html
        ):
            url = _decode_url(m.group(1))
            if url and url.startswith('http') and 'wecima' not in url:
                servers.append({
                    "name": f"Server {len(servers) + 1}",
                    "url": url,
                })

    # ── Pattern 6: iframe src ──
    if not servers:
        for m in re.finditer(
            r'<iframe[^>]*src=["\'](https?://[^"\']+)["\']',
            html, re.IGNORECASE
        ):
            url = m.group(1)
            if 'wecima' not in url and 'google' not in url and 'facebook' not in url:
                servers.append({
                    "name": f"Server {len(servers) + 1}",
                    "url": url,
                })

    # ── Pattern 7: Direct .mp4/.m3u8 URLs in the HTML ──
    if not servers:
        for m in re.finditer(
            r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*)',
            html
        ):
            url = m.group(1)
            if 'wecima' not in url:
                servers.append({
                    "name": f"Server {len(servers) + 1}",
                    "url": url,
                })
                break

    return _reorder_servers(servers)


def _extract_downloads(html: str) -> list[dict]:
    """Extract download links."""
    downloads = []
    for block in re.finditer(
        r'<li[^>]*class="download-item openLinkDown"[^>]*data-xpage="([^"]+)"[^>]*'
        r'data-href="([^"]+)"[^>]*>(.*?)</li>',
        html, re.DOTALL
    ):
        url = _decode_url(block.group(2))
        if not url:
            continue

        inner = block.group(3)

        res_m = re.search(r'<span class="resolution">(.*?)</span>', inner)
        resolution = res_m.group(1).strip() if res_m else ""

        size_m = re.search(r'<span class="size">(.*?)</span>', inner)
        size = size_m.group(1).strip() if size_m else ""

        quality_m = re.search(r'<span class="quality">(.*?)</span>', inner)
        quality = quality_m.group(1).strip() if quality_m else ""

        downloads.append({
            "name": resolution or "Download",
            "url": url,
            "resolution": resolution,
            "size": size,
            "quality": quality,
            "xpage": block.group(1),
        })
    return downloads


# ──────────────────────────────────────────────
#  Series — Seasons & Episodes
# ──────────────────────────────────────────────

def get_series_detail(url: str) -> dict:
    """Scrape series page for metadata + season info."""
    html = _fetch(url)
    if not html:
        return {"metadata": {}, "seasons": [], "episodes": []}

    metadata = _extract_metadata(html)
    post_id = _extract_series_post_id(html)
    seasons = _extract_seasons(html)

    # Parse episodes directly from the page
    episodes = _extract_episodes_from_html(html)

    if not seasons:
        num_seasons = metadata.get("numberOfSeasons") or 1
        seasons = [
            {"season_number": s, "name": f"Season {s}"}
            for s in range(1, int(num_seasons) + 1)
        ]

    return {
        "metadata": metadata,
        "post_id": post_id,
        "seasons": seasons,
        "episodes": episodes,
    }


def _extract_series_post_id(html: str) -> str | None:
    # This is the series id used by /ajax/Episode.  A generic data-post value
    # elsewhere on the page is only the reaction/post id and returns no data.
    m = re.search(
        r'class="[^"]*SeasonsEpisodes[^"]*"[^>]*data-id="(\d+)"', html
    )
    if m:
        return m.group(1)
    m = re.search(r'data-post="(\d+)"', html)
    return m.group(1) if m else None


def _extract_seasons(html: str) -> list[dict]:
    """Extract actual season numbers (which need not start at season 1)."""
    found = []
    seen = set()
    for m in re.finditer(
        r'class="[^"]*SeasonsEpisodes[^"]*"[^>]*data-season="season-(\d+)"',
        html,
    ):
        number = int(m.group(1))
        if number not in seen:
            seen.add(number)
            found.append({"season_number": number, "name": f"Season {number}"})
    return found


def _extract_episodes_from_html(html: str) -> list[dict]:
    """Parse episode links from the series page HTML."""
    episodes = []
    seen = set()
    for ep_m in re.finditer(r'<episodetitle>(.*?)</episodetitle>', html):
        pos = ep_m.start()
        before = html[:pos]
        a_pos = before.rfind("<a ")
        if a_pos < 0:
            continue
        tag = before[a_pos:]
        href_m = re.search(r'href="([^"]+)"', tag)
        if not href_m:
            continue
        href = href_m.group(1)
        if not href.startswith("http"):
            href = BASE + href
        name = ep_m.group(1).strip()
        if href not in seen:
            seen.add(href)
            episodes.append({
                "name": name,
                "url": href,
            })
    return episodes[::-1]  # newest first → oldest first


def get_season_episodes(post_id: str, season: int = 1) -> list[dict]:
    """Load episodes for a given season via AJAX."""
    html = _post_form(BASE + "/ajax/Episode", {
        "season": f"season-{season}",
        "post_id": post_id,
    })
    if not html:
        return []

    episodes = []
    for m in re.finditer(
        r'<a[^>]*href="((?:https?://[^"/]+)?/watch/[^"]+)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    ):
        href = m.group(1)
        if not href.startswith("http"):
            href = BASE + href
        name = re.sub(r'<[^>]+>', "", m.group(2)).strip()
        episodes.append({
            "name": name or f"Episode {len(episodes) + 1}",
            "url": href,
        })
    return episodes


# ──────────────────────────────────────────────
#  Trends
# ──────────────────────────────────────────────

def get_trends() -> list[dict]:
    html = _fetch(BASE + "/trends")
    if not html:
        return []
    return _parse_grid_items(html)
