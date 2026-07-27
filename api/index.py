import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from .akwam_api import AkwamAPI
from .egydead_api import EgyDeadAPI
from .faselhd_api import FaselhdAPI
from .wecima_api import (
    search as wecima_search,
    get_categories as wecima_categories,
    get_category_items as wecima_category_items,
    get_content_detail as wecima_detail,
    get_series_detail as wecima_series,
    get_season_episodes as wecima_episodes,
    get_homepage_tab as wecima_homepage,
    get_trends as wecima_trends,
)
from .sahid4u_api import (
    search as sahid4u_search,
    get_seasons as sahid4u_seasons,
    get_episodes as sahid4u_episodes,
    get_content_info as sahid4u_content_info,
    get_content_servers as sahid4u_servers,
    get_content_servers_and_downloads as sahid4u_servers_downloads,
    get_episode_series_info as sahid4u_episode_series_info,
)
from .royaldrama_api import (
    search as royaldrama_search,
    get_homepage as royaldrama_homepage,
    get_series as royaldrama_series,
    get_movies as royaldrama_movies,
    get_episodes_list as royaldrama_episodes_list,
    get_categories as royaldrama_categories,
    get_category_items as royaldrama_category_items,
    get_detail as royaldrama_detail,
)
from .video_resolver import VideoResolver, ResolvedVideo
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse, FileResponse, Response
import os
import httpx
import uuid
import time

app = FastAPI(title="Vortex Media API")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLIC_ASSETS = {
    "binance id  425075013.jpg": "binance id  425075013.jpg",
    "0xe21e3f2149caae5330702ca0e6cf6e66f668433f.jpg": "0xe21e3f2149caae5330702ca0e6cf6e66f668433f.jpg",
}

@app.get("/", response_class=FileResponse)
async def read_root():
    return os.path.join(os.path.dirname(__file__), "..", "index.html")

@app.get("/style.css")
async def get_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "style.css"))

@app.get("/app.js")
async def get_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "app.js"))

@app.get("/akwam-worker.js")
async def get_worker_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "akwam-worker.js"))

@app.get("/sahid4u-worker.js")
async def get_sahid4u_worker_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "sahid4u-worker.js"))

@app.get("/faselhd-worker.js")
async def get_faselhd_worker_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "faselhd-worker.js"))

@app.get("/favicon.svg")
async def get_favicon():
    return FileResponse(os.path.join(PROJECT_ROOT, "favicon.svg"))

@app.get("/static/{filename:path}")
async def get_public_asset(filename: str):
    asset = PUBLIC_ASSETS.get(filename)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(os.path.join(PROJECT_ROOT, asset))


# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

akwam = AkwamAPI()
egydead = EgyDeadAPI()
faselhd = FaselhdAPI()
video_resolver = VideoResolver()

# ------------------------------------------------------------------ #
#  Shared models
# ------------------------------------------------------------------ #

class LinkRequest(BaseModel):
    url: str

class ResolveEmbedRequest(BaseModel):
    url: str
    quality: Optional[str] = None  # 'best', '1080p', '720p', '480p'
    # Forwarded end-user session (from the partner site) so gated players
    # (Mixdrop / vinovo / shaaheid4u) can load their source server-side.
    cookies: Optional[List[dict]] = None
    referer: Optional[str] = None

class DownloadRequest(BaseModel):
    url: str
    filename: Optional[str] = None

# ------------------------------------------------------------------ #
#  Akwam endpoints  (unchanged)
# ------------------------------------------------------------------ #

@app.get("/api/search")
async def search(q: str, type: str = "movie"):
    try:
        results = akwam.search(q, type)
        # Tag each result with its source
        for r in results:
            r['source'] = 'akwam'
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/episodes")
async def get_episodes(req: LinkRequest):
    try:
        episodes = akwam.get_episodes(req.url)
        return {"episodes": episodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qualities")
async def get_qualities(req: LinkRequest):
    try:
        qualities = akwam.get_qualities(req.url)
        return {"qualities": qualities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resolve")
async def resolve(req: LinkRequest):
    try:
        url = akwam.resolve_direct_url(req.url)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _resolve_watch_url(target_url: str):
    """Extract direct MP4 URL from an Akwam watch/download page.

    New site structure:
      Watch page: <source src="https://s{id}.downet.net/.../{slug}.mp4" ...>
      Download page: <a href="https://s{id}.downet.net/.../{slug}.mp4" download ...>

    Returns (mp4_url, page_url) or (None, None).
    """
    import re as _re
    import requests as _req

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        r = _req.get(target_url, headers=headers, timeout=30)
        html = r.content.decode('utf-8', errors='replace')

        src = _re.search(r'<source\s+src=["\']([^"\']+\.mp4)["\']', html)
        if src:
            return src.group(1), target_url

        href = _re.search(r'href=["\']([^"\']+\.mp4)["\'][^>]*download', html)
        if href:
            return href.group(1), target_url

        any_mp4 = _re.search(r'href=["\']([^"\']+\.mp4)["\']', html)
        if any_mp4:
            return any_mp4.group(1), target_url

        any_mkv = _re.search(r'href=["\']([^"\']+\.mkv)["\']', html)
        if any_mkv:
            return any_mkv.group(1), target_url

        return None, None
    except Exception:
        return None, None


@app.get("/api/akwam-resolve-stream")
async def akwam_resolve_stream(url: str):
    """Resolve an Akwam watch/download URL to a direct MP4 URL.

    The new Akwam site embeds direct MP4 URLs in the HTML of watch/download
    pages — no JavaScript execution needed.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")

    if not url.startswith('http'):
        url = 'https://' + url

    loop = asyncio.get_event_loop()
    mp4_url, referer = await loop.run_in_executor(None, _resolve_watch_url, url)

    if not mp4_url:
        raise HTTPException(
            status_code=502,
            detail="Could not resolve a streamable URL from Akwam"
        )

    return {"url": mp4_url, "referer": referer}


@app.get("/api/akwam-stream")
async def akwam_stream(url: str, request: Request):
    """Resolve an Akwam page and proxy its media with byte-range support.

    Some Downet shards currently present an incomplete TLS chain, which makes
    an otherwise valid direct MP4 fail in browsers.  The provider keeps its
    TLS workaround scoped to ``*.downet.net``; this endpoint exposes that
    working connection as a normal same-origin video stream.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme not in ('http', 'https') or not hostname:
        raise HTTPException(status_code=400, detail="Invalid Akwam URL")
    allowed_akwam_hosts = {'ak.sv', 'akwam.it', 'akwam.to'}
    if hostname not in allowed_akwam_hosts:
        raise HTTPException(status_code=403, detail="Only Akwam pages are allowed")

    loop = asyncio.get_event_loop()
    upstream, info = await loop.run_in_executor(
        None, akwam.stream_video, url, request.headers.get('range'))
    # ``requests.Response`` is falsey for 4xx/5xx statuses.  Keep a real
    # upstream response so range errors such as 416 reach the browser with
    # their Content-Range metadata instead of being collapsed into a 502.
    if upstream is None or not info:
        raise HTTPException(status_code=502, detail="Could not open Akwam stream")

    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Accept-Ranges': info.get('accept_ranges') or 'bytes',
        'Cache-Control': 'no-store',
    }
    if info.get('content_length'):
        response_headers['Content-Length'] = info['content_length']
    if info.get('content_range'):
        response_headers['Content-Range'] = info['content_range']

    def stream_body():
        try:
            yield from upstream.iter_content(chunk_size=65536)
        finally:
            upstream.close()

    return StreamingResponse(
        stream_body(),
        status_code=info['status_code'],
        media_type=info['content_type'],
        headers=response_headers,
    )


class BulkResolveRequest(BaseModel):
    urls: List[Dict[str, str]] # List of {name: "...", url: "..."}

@app.post("/api/bulk-resolve")
async def bulk_resolve(req: BulkResolveRequest):
    """
    Bulk-resolve episode download links.

    For each episode URL:
      1. Fetch available qualities from the episode page.
      2. Pick the best quality (720p preferred, else first available).
      3. Call resolve_direct_url on the link_id — this now returns either:
         - A direct .mp4 URL (if the CDN server redirects directly), OR
         - The akwam /download/ countdown page URL (JS-gated fallback).
      4. Also fetch all available download server links via get_download_links.

    Returns a list of {name, url, quality, size, download_links}.
    """
    try:
        loop = asyncio.get_event_loop()

        # Step 1: Get qualities for all episodes in parallel
        quality_tasks = [
            loop.run_in_executor(None, akwam.get_qualities, item['url'])
            for item in req.urls
        ]
        all_qualities = await asyncio.gather(*quality_tasks)

        # Step 2: Build resolve + download-links tasks for episodes that have qualities
        resolve_tasks = []
        dl_links_tasks = []
        episode_names = []
        episode_qualities = []

        for i, qualities in enumerate(all_qualities):
            best_q = next((q for q in qualities if q['quality'] == '720p'), None)
            if not best_q and qualities:
                best_q = qualities[0]
            if best_q:
                episode_names.append(req.urls[i]['name'])
                episode_qualities.append(best_q)
                resolve_tasks.append(
                    loop.run_in_executor(None, akwam.resolve_direct_url, best_q['link_id'])
                )
                dl_links_tasks.append(
                    loop.run_in_executor(None, akwam.get_download_links, best_q['link_id'])
                )

        # Step 3: Resolve all in parallel
        direct_urls, all_dl_links = await asyncio.gather(
            asyncio.gather(*resolve_tasks),
            asyncio.gather(*dl_links_tasks),
        )

        # Step 4: Build results
        results = []
        for name, url, quality, dl_links in zip(
            episode_names, direct_urls, episode_qualities, all_dl_links
        ):
            if url:
                results.append({
                    "name": name,
                    "url": url,                            # primary URL (direct or download page)
                    "quality": quality.get('quality', '720p'),
                    "size": quality.get('size', ''),
                    "download_links": dl_links,            # all available CDN servers
                })

        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  EgyDead endpoints
# ------------------------------------------------------------------ #

@app.get("/api/egydead/search")
async def egydead_search(q: str):
    """Search EgyDead for movies, series, seasons and episodes."""
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, egydead.search, q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/egydead/seasons")
async def egydead_seasons(req: LinkRequest):
    """Get seasons list for an EgyDead series page."""
    try:
        loop = asyncio.get_event_loop()
        seasons = await loop.run_in_executor(None, egydead.get_seasons, req.url)
        return {"seasons": seasons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/egydead/episodes")
async def egydead_episodes(req: LinkRequest):
    """Get episode list for an EgyDead season page."""
    try:
        loop = asyncio.get_event_loop()
        episodes = await loop.run_in_executor(None, egydead.get_episodes, req.url)
        return {"episodes": episodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/egydead/watch")
async def egydead_watch(req: LinkRequest):
    """Extract embed / direct stream URLs from a movie or episode page."""
    try:
        loop = asyncio.get_event_loop()
        watch_data = await loop.run_in_executor(None, egydead.get_watch_url, req.url)
        return watch_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  Wecima endpoints
# ------------------------------------------------------------------ #

class WecimaSlugRequest(BaseModel):
    slug: str
    page: Optional[int] = 1

class WecimaSeasonRequest(BaseModel):
    post_id: str
    season: int = 1

@app.get("/api/wecima/search")
async def wecima_search_ep(q: str):
    """Search Wecima for movies and series."""
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, wecima_search, q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wecima/categories")
async def wecima_list_categories():
    """List all available Wecima categories."""
    try:
        return {"categories": wecima_categories()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wecima/category")
async def wecima_category(req: WecimaSlugRequest):
    """Get items from a specific category page."""
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(
            None, wecima_category_items, req.slug, req.page
        )
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wecima/detail")
async def wecima_content_detail(req: LinkRequest):
    """Get movie/episode detail: servers + downloads + metadata."""
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, wecima_detail, req.url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wecima/series")
async def wecima_series_detail(req: LinkRequest):
    """Get series metadata and season list."""
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, wecima_series, req.url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wecima/episodes")
async def wecima_season_episodes(req: WecimaSeasonRequest):
    """Get episodes for a given season of a series."""
    try:
        loop = asyncio.get_event_loop()
        episodes = await loop.run_in_executor(
            None, wecima_episodes, req.post_id, req.season
        )
        return {"episodes": episodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wecima/homepage")
async def wecima_homepage_ep(tab: str = "new"):
    """Get homepage content by tab: new, movies, series, episodes."""
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, wecima_homepage, tab)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wecima/trends")
async def wecima_trends_ep():
    """Get trending content."""
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, wecima_trends)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  Sahid4u endpoints (server-side fallback)
# ------------------------------------------------------------------ #

@app.get("/api/sahid4u/search")
async def sahid4u_search_ep(q: str):
    """Search Sahid4u for movies and series."""
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, sahid4u_search, q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sahid4u/seasons")
async def sahid4u_seasons_ep(req: LinkRequest):
    """Get seasons for a Sahid4u series page."""
    try:
        loop = asyncio.get_event_loop()
        seasons = await loop.run_in_executor(None, sahid4u_seasons, req.url)
        return {"seasons": seasons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sahid4u/episodes")
async def sahid4u_episodes_ep(req: LinkRequest):
    """Get episodes for a Sahid4u season page."""
    try:
        loop = asyncio.get_event_loop()
        episodes = await loop.run_in_executor(None, sahid4u_episodes, req.url)
        return {"episodes": episodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sahid4u/watch")
async def sahid4u_watch_ep(req: LinkRequest):
    """Get servers and download info for a Sahid4u content page."""
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, sahid4u_servers_downloads, req.url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sahid4u/episode-series-info")
async def sahid4u_episode_series_info_ep(req: LinkRequest):
    """Get series and season info from an episode page."""
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, sahid4u_episode_series_info, req.url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  FaselHD endpoints
# ------------------------------------------------------------------ #

class FaselhdCategorySlugRequest(BaseModel):
    slug: str
    page: Optional[int] = 1

@app.get("/api/faselhd/search")
async def faselhd_search(q: str):
    """Search FaselHD."""
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, faselhd.search, q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/faselhd/categories")
async def faselhd_categories():
    """List FaselHD categories."""
    try:
        loop = asyncio.get_event_loop()
        cats = await loop.run_in_executor(None, faselhd.get_categories)
        return {"categories": cats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/faselhd/category")
async def faselhd_category_posts(req: FaselhdCategorySlugRequest):
    """Get posts in a FaselHD category."""
    try:
        loop = asyncio.get_event_loop()
        posts = await loop.run_in_executor(None, faselhd.get_category_posts, req.slug, req.page)
        return {"posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/faselhd/post/{post_id}")
async def faselhd_post_detail(post_id: int):
    """Get details for a FaselHD post by ID."""
    try:
        loop = asyncio.get_event_loop()
        detail = await loop.run_in_executor(None, faselhd.get_post_detail, post_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Post not found")
        return detail
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/faselhd/servers/{post_id}")
async def faselhd_get_servers(post_id: int):
    """Get available servers/embeds for a FaselHD post."""
    try:
        loop = asyncio.get_event_loop()
        # The WordPress post ID is not the player POST_ID expected by
        # ajax.php. get_post_detail fetches the canonical post page first and
        # lets _get_servers translate it, just like the main FaselHD UI path.
        detail = await loop.run_in_executor(None, faselhd.get_post_detail, post_id)
        return {"servers": (detail or {}).get("servers", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/faselhd/series/{slug}")
async def faselhd_series(slug: str):
    """Get series structure (seasons & episodes) for a FaselHD series."""
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, faselhd.get_series_structure, slug)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/faselhd/trending")
async def faselhd_trending():
    """Get trending content from FaselHD."""
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, faselhd.get_trending)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/faselhd/resolve")
async def faselhd_resolve(req: LinkRequest):
    """Resolve a FaselHD embed URL to direct video URL."""
    try:
        loop = asyncio.get_event_loop()
        # Try FaselHD-specific resolvers first
        result = await loop.run_in_executor(None, lambda: faselhd.resolve_govid_embed(req.url, None))
        if not result:
            result = await loop.run_in_executor(None, faselhd.resolve_embed, req.url)
        # Fall back to generic VideoResolver (which includes browser fallback)
        if not result:
            resolved = await video_resolver.resolve(req.url)
            if resolved:
                result = {
                    'url': resolved.url,
                    'title': resolved.title,
                    'ext': resolved.ext,
                    'quality': resolved.quality,
                    'filesize': resolved.filesize,
                }
        return result or {"error": "Could not resolve embed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  Royal-Drama endpoints
# ------------------------------------------------------------------ #

@app.get("/api/royaldrama/search")
async def royaldrama_search_ep(q: str):
    """Search Royal-Drama (best-effort — the site's search is bot-protected)."""
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, royaldrama_search, q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/royaldrama/home")
async def royaldrama_home_ep():
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, royaldrama_homepage)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/royaldrama/series")
async def royaldrama_series_ep(page: int = 1):
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, royaldrama_series, page)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/royaldrama/movies")
async def royaldrama_movies_ep(page: int = 1):
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, royaldrama_movies, page)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/royaldrama/episodes")
async def royaldrama_episodes_ep(page: int = 1):
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, royaldrama_episodes_list, page)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/royaldrama/categories")
async def royaldrama_categories_ep():
    return {"categories": royaldrama_categories()}

@app.get("/api/royaldrama/category")
async def royaldrama_category_ep(slug: str):
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, royaldrama_category_items, slug)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/royaldrama/detail")
async def royaldrama_detail_ep(url: str):
    """Get metadata + episodes + a server link for a Royal-Drama watch page."""
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, royaldrama_detail, url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  Sahid4u endpoints
# ------------------------------------------------------------------ #

@app.post("/api/sahid4u/servers")
async def sahid4u_servers_ep(req: LinkRequest):
    """Get watch servers for a Sahid4u content URL."""

    try:
        loop = asyncio.get_event_loop()
        servers = await loop.run_in_executor(None, sahid4u_servers, req.url)
        return {"servers": servers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sahid4u/info")
async def sahid4u_info_ep(req: LinkRequest):
    """Get content info (title, watch/download URLs)."""

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, sahid4u_content_info, req.url)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  Video Resolver endpoint
#  Resolves embed player URLs to direct video URLs using yt-dlp.
# ------------------------------------------------------------------ #

@app.post("/api/resolve-embed")
async def resolve_embed(req: ResolveEmbedRequest):
    """
    Resolve an embed player URL to a direct video URL.
    
    Uses yt-dlp to extract the direct video URL from embed players
    like uqload, doodstream, streamtape, etc.
    
    This bypasses the ad-heavy embed page entirely.
    """
    if not req.url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")

    try:
        result = None
        used_specific_resolver = False
        embed_hostname = (_up.urlparse(req.url).hostname or '').lower()
        if embed_hostname == 'govid.live' or embed_hostname.endswith('.govid.live'):
            # FaselHD's Govid wrapper exposes the real HLS source as hex JS.
            # Its focused extractor is much faster and more reliable than the
            # generic yt-dlp/browser chain.
            loop = asyncio.get_event_loop()
            specific = await loop.run_in_executor(
                None, faselhd.resolve_govid_embed, req.url, None)
            if specific and specific.get('url') and specific.get('type') in ('hls', 'mp4'):
                used_specific_resolver = True
                result = ResolvedVideo(
                    url=specific['url'],
                    ext='m3u8' if specific['type'] == 'hls' else 'mp4',
                )
        if result is None:
            result = await video_resolver.resolve(
                req.url, cookies=req.cookies, referer=req.referer)
        if not result:
            raise HTTPException(
                status_code=502, 
                detail="Could not resolve video URL from embed"
            )
        
        response = {
            "url": result.url,
            "title": result.title,
            "ext": result.ext,
            "quality": result.quality,
            "filesize": result.filesize,
            "formats": result.formats,
        }
        from urllib.parse import quote
        embed_host = f"{_up.urlparse(req.url).scheme}://{_up.urlparse(req.url).netloc}"
        # Cookie-backed results need the session proxy.  Media CDNs generally
        # validate the embed origin, while req.referer is only the partner page
        # used to unlock the embed itself.
        if req.cookies:
            sid = _store_session(req.cookies, embed_host + '/', embed_host)
            # result.url is the captured media URL (m3u8 manifest OR direct file).
            target = result.url
            response["proxy_url"] = (
                f"/api/media-proxy?sid={sid}&url={quote(target, safe='')}"
            )
        elif result.ext == 'm3u8':
            if used_specific_resolver:
                # Govid already yielded the final manifest; do not repeat the
                # much slower browser extraction on its wrapper URL.
                response["proxy_url"] = (
                    f"/api/hls-seg?url={quote(result.url, safe='')}"
                    f"&ref={quote(req.url, safe='')}"
                )
            else:
                # Standard JS-only HLS: capture player state/cookies on demand.
                response["proxy_url"] = f"/api/hls-proxy?url={quote(req.url, safe='')}"
        else:
            # Direct files are also proxied so CORS, TLS and Referer policy are
            # consistent across hosts and byte-range seeking keeps working.
            response["proxy_url"] = (
                f"/api/proxy-stream?url={quote(result.url, safe='')}"
                f"&referer={quote(embed_host + '/', safe='')}"
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  EgyDead Download endpoint
#  Resolves embed URL and streams video directly as a file download.
# ------------------------------------------------------------------ #

@app.post("/api/egydead/download")
async def egydead_download(req: DownloadRequest):
    """
    Download a video from an EgyDead embed URL.
    
    Resolves the embed URL and streams the video directly to the client
    as a file download, bypassing all ads.
    """
    if not req.url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")

    try:
        # Resolve embed URL
        resolved = await video_resolver.resolve(req.url)
        if not resolved:
            raise HTTPException(status_code=502, detail="Could not resolve video URL")

        # Stream the video as a download
        filename = req.filename or f"{resolved.title or 'video'}.{resolved.ext or 'mp4'}"
        
        async def download_generator():
            async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=120.0) as client:
                response = await client.get(resolved.url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': req.url,
                })
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    yield chunk

        return StreamingResponse(
            download_generator(),
            media_type='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Access-Control-Allow-Origin': '*',
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  Proxy Stream endpoint
#  Downloads from the embed server and streams to the client,
#  preventing ad redirects and enabling server-side caching.
# ------------------------------------------------------------------ #

@app.get("/api/proxy-stream")
async def proxy_stream(url: str, request: Request, referer: str = ""):
    """Proxy a video stream through the server.
    
    This downloads the video from the remote server and streams it to the
    client. This avoids:
    - Ad popups from embed players
    - CORS issues
    - Referrer-based blocking
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")

    # Validate URL to prevent SSRF attacks
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL")
    # Block internal network access (basic SSRF prevention)
    hostname = parsed.hostname.lower()
    blocked = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '169.254']
    if any(hostname.startswith(b) for b in blocked) or hostname.endswith('.local'):
        raise HTTPException(status_code=403, detail="Access denied")

    # Forward Range header for seeking support
    range_header = request.headers.get('range')
    ref = url
    if referer:
        ref_parsed = urlparse(referer)
        if ref_parsed.scheme in ('http', 'https') and ref_parsed.hostname:
            ref = referer
    ref_parsed = urlparse(ref)
    origin = f"{ref_parsed.scheme}://{ref_parsed.netloc}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': ref,
        'Origin': origin,
        'Accept': '*/*',
    }
    if range_header:
        headers['Range'] = range_header

    try:
        client = httpx.AsyncClient(follow_redirects=True, verify=False, timeout=httpx.Timeout(30.0, read=120.0))

        # Stream the response
        req = client.build_request('GET', url, headers=headers)
        response = await client.send(req, stream=True)

        # Determine content type
        content_type = response.headers.get('content-type', 'video/mp4')
        content_length = response.headers.get('content-length')
        content_range = response.headers.get('content-range')
        accept_ranges = response.headers.get('accept-ranges', 'bytes')

        resp_headers = {
            'Content-Type': content_type,
            'Accept-Ranges': accept_ranges,
            'Access-Control-Allow-Origin': '*',
            # Resolved host URLs are usually signed and short-lived.
            'Cache-Control': 'no-store',
        }
        if content_length:
            resp_headers['Content-Length'] = content_length
        if content_range:
            resp_headers['Content-Range'] = content_range

        status_code = response.status_code

        async def stream_generator():
            try:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        return StreamingResponse(
            stream_generator(),
            status_code=status_code,
            headers=resp_headers,
            media_type=content_type
        )
    except httpx.HTTPError as e:
        if 'response' in locals():
            await response.aclose()
        if 'client' in locals():
            await client.aclose()
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------ #
#  HLS Proxy  (for EarnVids-style / JS-only embed hosts)
#  These hosts serve an HLS manifest that is referer-locked to the embed
#  host and rotates on a short TTL, so a plain direct link is unusable.
#  We capture a fresh manifest in a browser session, then proxy the
#  manifest + every variant/segment through our server (injecting the
#  required Referer) so the client can play it.
# ------------------------------------------------------------------ #

import urllib.parse as _up

_HLS_SEG_CT = 'application/vnd.apple.mpegurl'


# ------------------------------------------------------------------ #
#  Session store for forwarded user cookies/referer
#  (used by /api/media-proxy to replay a gated host's session)
# ------------------------------------------------------------------ #
SESSION_STORE: dict = {}
SESSION_TTL = 1800  # seconds
SESSION_MAX = 256


def _store_session(cookies, referer, host):
    now = time.time()
    expired = [key for key, value in SESSION_STORE.items()
               if now - value.get('ts', 0) > SESSION_TTL]
    for key in expired:
        SESSION_STORE.pop(key, None)
    while len(SESSION_STORE) >= SESSION_MAX:
        oldest = min(SESSION_STORE, key=lambda key: SESSION_STORE[key].get('ts', 0))
        SESSION_STORE.pop(oldest, None)
    sid = uuid.uuid4().hex
    SESSION_STORE[sid] = {
        'cookies': cookies or [],
        'referer': referer,
        'host': host,
        'ts': now,
    }
    return sid


def _get_session(sid):
    s = SESSION_STORE.get(sid)
    if not s:
        return None
    now = time.time()
    if now - s['ts'] > SESSION_TTL:
        SESSION_STORE.pop(sid, None)
        return None
    # Sessions back active HLS playback, so expiry and capacity eviction must
    # be based on the most recent segment request rather than creation time.
    s['ts'] = now
    return s


def _cookie_dict_for(cookies, target_host):
    """Build a name->value dict of cookies whose domain matches target_host."""
    out = {}
    for c in (cookies or []):
        if not isinstance(c, dict) or not c.get('name'):
            continue
        dom = (c.get('domain') or c.get('host') or '').lstrip('.')
        if dom and not (target_host == dom or target_host.endswith('.' + dom)):
            continue
        out[c['name']] = str(c.get('value', ''))
    return out


@app.get("/api/hls-proxy")
async def hls_proxy(url: str, referer: str = ""):
    """Capture a fresh HLS manifest for an embed URL and serve a
    rewritten playlist whose segments point back at our segment proxy."""
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL")

    loop = asyncio.get_event_loop()
    captured = await loop.run_in_executor(
        None, lambda: __import__('api.browser_extractor', fromlist=['capture_hls_manifest']).capture_hls_manifest(url, referer=referer or None)
    )
    if not captured:
        raise HTTPException(status_code=502, detail="Could not capture HLS manifest")

    if isinstance(captured, tuple):
        manifest = captured[0]
        raw = captured[1] if len(captured) > 1 else None
        effective_referer = captured[2] if len(captured) > 2 else None
        captured_cookies = captured[3] if len(captured) > 3 else []
    else:
        manifest, raw, effective_referer, captured_cookies = captured, None, None, []

    # The CDN serves the manifest/segments and requires the Referer to be the
    # EMBED host (e.g. callistanise.com), not the random manifest CDN host.
    embed_referer = effective_referer or url
    embed_parts = _up.urlparse(embed_referer)
    embed_origin = f"{embed_parts.scheme}://{embed_parts.netloc}"

    # Prefer the manifest content captured in-session (avoids a second,
    # TTL-limited fetch). Fall back to a fresh fetch if needed.
    if not raw or '#EXTM3U' not in raw:
        try:
            async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=30.0) as client:
                resp = await client.get(
                    manifest,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                                      'Chrome/120.0.0.0 Safari/537.36',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': embed_referer,
                        'Origin': embed_origin,
                        'Accept': '*/*',
                    },
                )
                raw = resp.text
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream manifest error: {str(e)}")

    if not raw or '#EXTM3U' not in raw:
        raise HTTPException(status_code=502, detail="Captured manifest was empty/expired")

    if captured_cookies:
        sid = _store_session(captured_cookies, embed_referer, embed_origin)
        rewritten = _rewrite_hls_to(
            raw,
            manifest,
            lambda target: (
                f"/api/media-proxy?sid={sid}"
                f"&url={_up.quote(target, safe='')}"
            ),
        )
    else:
        rewritten = _rewrite_hls(raw, manifest, embed_referer)
    return Response(
        content=rewritten,
        media_type=_HLS_SEG_CT,
        headers={'Access-Control-Allow-Origin': '*', 'Cache-Control': 'no-store'},
    )


@app.get("/api/hls-seg")
async def hls_segment(url: str, request: Request, ref: str = ""):
    """Proxy a single HLS variant/segment through our server, injecting the
    Referer required by the embed host's CDN."""
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL")
    hostname = parsed.hostname.lower()
    blocked = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '169.254']
    if any(hostname.startswith(b) for b in blocked) or hostname.endswith('.local'):
        raise HTTPException(status_code=403, detail="Access denied")

    referrer = ref or f"{parsed.scheme}://{parsed.netloc}/"
    ref_parts = urlparse(referrer)
    ref_origin = f"{ref_parts.scheme}://{ref_parts.netloc}"
    try:
        upstream_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': referrer,
            'Origin': ref_origin,
            'Accept': '*/*',
        }
        range_header = request.headers.get('Range')
        if range_header:
            upstream_headers['Range'] = range_header
        async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=httpx.Timeout(30.0, read=120.0)) as client:
            resp = await client.get(
                url,
                headers=upstream_headers,
            )
            content_type = resp.headers.get('content-type', 'video/mp2t')
            body = resp.content
            if ('mpegurl' in content_type.lower()
                    or (body and body[:200].lstrip().startswith(b'#EXTM3U'))):
                rewritten = _rewrite_hls(
                    body.decode('utf-8', 'replace'), url, referrer)
                return Response(
                    content=rewritten,
                    media_type=_HLS_SEG_CT,
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Cache-Control': 'no-store',
                    },
                )
            response_headers = {
                'Access-Control-Allow-Origin': '*',
                'Accept-Ranges': resp.headers.get('accept-ranges', 'bytes'),
                'Cache-Control': 'no-store',
            }
            for source, target in (
                ('content-range', 'Content-Range'),
                ('content-length', 'Content-Length'),
            ):
                if resp.headers.get(source):
                    response_headers[target] = resp.headers[source]
            return Response(
                content=body,
                status_code=resp.status_code,
                media_type=content_type,
                headers=response_headers,
            )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/media-proxy")
async def media_proxy(sid: str, url: str, request: Request):
    """Replay a forwarded user session (cookies/referer) to fetch a gated
    host's media. For HLS manifests, the playlist is rewritten so every
    variant/segment also goes through this proxy with the same session."""
    s = _get_session(sid)
    if not s:
        raise HTTPException(status_code=403, detail="Invalid or expired session")

    from urllib.parse import urlparse as _p
    parsed = _p(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL")
    hostname = parsed.hostname.lower()
    blocked = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '169.254']
    if any(hostname.startswith(b) for b in blocked) or hostname.endswith('.local'):
        raise HTTPException(status_code=403, detail="Access denied")

    target_host = hostname
    cookie_dict = _cookie_dict_for(s['cookies'], target_host)
    referer = s['referer'] or s['host'] or url
    origin = s['host'] or f"{parsed.scheme}://{parsed.netloc}"
    headers = {
        # Some signed CDNs (currently Vidoba's cdnz.quest transport) bind the
        # URL to the browser request fingerprint used during capture.  Keep
        # these values aligned with browser_extractor's Chromium context.
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': referer,
        'Origin': origin.rstrip('/'),
        'Accept': '*/*',
    }
    range_hdr = request.headers.get('Range')
    if range_hdr:
        headers['Range'] = range_hdr

    try:
        client = httpx.AsyncClient(
            follow_redirects=True, verify=False,
            timeout=httpx.Timeout(30.0, read=120.0),
        )
        req = client.build_request(
            'GET', url, headers=headers, cookies=cookie_dict)
        resp = await client.send(req, stream=True)
        ct = resp.headers.get('content-type', '')
        media_name = parsed.path.lower().rsplit('/', 1)[-1]
        looks_like_hls = (
            'mpegurl' in ct.lower()
            or media_name.endswith(('.m3u8', '.m3u'))
            or media_name == 'master.txt'
            or 'playlist' in media_name
            or 'manifest' in media_name
            or 'urlset' in media_name
        )
        byte_iterator = None
        first_chunk = b''
        collected_hls = None
        if not looks_like_hls and (
                not ct or 'octet-stream' in ct.lower() or ct.lower().startswith('text/')):
            byte_iterator = resp.aiter_bytes(chunk_size=65536)
            try:
                first_chunk = await anext(byte_iterator)
            except StopAsyncIteration:
                first_chunk = b''
            if first_chunk[:200].lstrip().startswith(b'#EXTM3U'):
                looks_like_hls = True
                remainder = b''.join([chunk async for chunk in byte_iterator])
                collected_hls = first_chunk + remainder
        if looks_like_hls:
            try:
                raw_body = collected_hls if collected_hls is not None else await resp.aread()
                body = raw_body.decode('utf-8', 'replace')
            finally:
                await resp.aclose()
                await client.aclose()
            if body and body[:200].lstrip().startswith('#EXTM3U'):
                rewritten = _rewrite_hls_to(
                    body,
                    url,
                    lambda u: f"/api/media-proxy?sid={sid}&url={_up.quote(u, safe='')}",
                )
                return Response(
                    content=rewritten,
                    media_type=_HLS_SEG_CT,
                    headers={'Access-Control-Allow-Origin': '*', 'Cache-Control': 'no-store'},
                )
            raise HTTPException(status_code=502, detail="Upstream HLS manifest was invalid")

        response_headers = {
            'Access-Control-Allow-Origin': '*',
            'Accept-Ranges': resp.headers.get('Accept-Ranges', 'bytes'),
            'Cache-Control': 'no-store',
        }
        for header in ('Content-Range', 'Content-Length', 'ETag', 'Last-Modified'):
            value = resp.headers.get(header)
            if value:
                response_headers[header] = value

        async def stream_body():
            try:
                if first_chunk:
                    yield first_chunk
                iterator = byte_iterator or resp.aiter_bytes(chunk_size=65536)
                async for chunk in iterator:
                    yield chunk
            finally:
                await resp.aclose()
                await client.aclose()

        return StreamingResponse(
            stream_body(),
            status_code=resp.status_code,
            media_type=ct or 'application/octet-stream',
            headers=response_headers,
        )
    except httpx.HTTPError as e:
        if 'resp' in locals():
            await resp.aclose()
        if 'client' in locals():
            await client.aclose()
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        if 'resp' in locals():
            await resp.aclose()
        if 'client' in locals():
            await client.aclose()
        raise HTTPException(status_code=500, detail=str(e))


def _rewrite_hls_to(text: str, manifest_url: str, proxy_for) -> str:
    """Rewrite every URL in an HLS playlist through the given proxy builder."""
    import re as _re
    base = _up.urljoin(manifest_url, '.')
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            # Directives may carry a URI="..." attribute that also needs rewriting
            def _rewrite_uri(m, _base=base):
                return f'URI="{proxy_for(_up.urljoin(_base, m.group(1)))}"'
            out.append(_re.sub(r'URI="([^"]+)"', _rewrite_uri, line))
            continue
        out.append(proxy_for(_up.urljoin(base, stripped)))
    return "\n".join(out) + "\n"


def _rewrite_hls(text: str, manifest_url: str, embed_referer: str) -> str:
    """Rewrite every URL in an HLS playlist to go through /api/hls-seg."""
    return _rewrite_hls_to(
        text, manifest_url,
        lambda u: "/api/hls-seg?url=" + _up.quote(u, safe="")
        + "&ref=" + _up.quote(embed_referer, safe=""),
    )


# ------------------------------------------------------------------ #
#  Image Proxy (for CORS-blocked thumbnails)
# ------------------------------------------------------------------ #

@app.get("/api/proxy-image")
async def proxy_image(url: str):
    """Proxy an image through the server to bypass CORS restrictions."""
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")

    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL")
    hostname = parsed.hostname.lower()
    blocked = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '169.254']
    if any(hostname.startswith(b) for b in blocked) or hostname.endswith('.local'):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': url,
            })
            content_type = resp.headers.get('content-type', 'image/jpeg')
            return StreamingResponse(
                iter([resp.content]),
                media_type=content_type,
                headers={
                    'Cache-Control': 'public, max-age=86400',
                    'Access-Control-Allow-Origin': '*',
                }
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

# ------------------------------------------------------------------ #
#  CORS Proxy (dumb pipe for client-side AkwamWorker fallback)
#  No parsing, no chaining — just forwards raw HTML to the browser.
# ------------------------------------------------------------------ #

@app.get("/api/cors-proxy")
async def cors_proxy(url: str):
    """Lightweight CORS proxy — forwards a URL's HTML to the browser.
    
    Used as a last-resort fallback when public CORS proxies
    (corsproxy.io, allorigins.win) fail. The browser does all parsing.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")

    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL")
    # Block internal network access (SSRF prevention)
    hostname = parsed.hostname.lower()
    blocked = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '169.254']
    if any(hostname.startswith(b) for b in blocked) or hostname.endswith('.local'):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=25.0) as client:
            resp = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            })
            content_type = resp.headers.get('content-type', 'text/html')
            from fastapi.responses import Response
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'public, max-age=300',
                }
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

# ------------------------------------------------------------------ #
#  Health
# ------------------------------------------------------------------ #

@app.get("/api/health")
async def health():
    return {"status": "ok"}
