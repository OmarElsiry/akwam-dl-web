import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from .akwam_api import AkwamAPI
from .egydead_api import EgyDeadAPI
from .video_resolver import VideoResolver, ResolvedVideo
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import httpx

app = FastAPI(title="Vortex Media API")

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

# Mount static files from project root
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..")), name="static")


# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

akwam = AkwamAPI()
egydead = EgyDeadAPI()
video_resolver = VideoResolver()

# ------------------------------------------------------------------ #
#  Shared models
# ------------------------------------------------------------------ #

class LinkRequest(BaseModel):
    url: str

class ResolveEmbedRequest(BaseModel):
    url: str
    quality: Optional[str] = None  # 'best', '1080p', '720p', '480p'

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

# ------------------------------------------------------------------ #
#  Akwam Playwright stream proxy
#  Uses a headless Chromium browser to navigate the Akwam download
#  page, execute the JS countdown that activates the CDN token, then
#  stream the actual video file back to the client.
# ------------------------------------------------------------------ #

import threading
_pw_lock = threading.Lock()

def _playwright_get_video_url(link_id_url: str):
    """
    Use Playwright headless browser to:
      1. Navigate the /link/ page → get download page URLs
      2. Navigate the download page → let JS execute (2.2s countdown)
      3. Extract the activated download URL
      4. Return (download_url, cookies, headers) for streaming
    """
    from playwright.sync_api import sync_playwright
    import re as _re

    url = 'https://' + link_id_url

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
        )
        page = context.new_page()

        try:
            # Step 1: Visit /link/ page to get download page URLs
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            html1 = page.content()

            dl_links = list(dict.fromkeys(
                _re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)
            ))
            if not dl_links:
                browser.close()
                return None, None, None

            # Step 2: Navigate to the first download page
            download_url = dl_links[0]
            page.goto(download_url, wait_until='domcontentloaded', timeout=30000)

            # Step 3: Wait for the countdown (2.2s) + buffer
            page.wait_for_timeout(8000)

            # Step 4: Get the activated download href
            html2 = page.content()
            mp4_matches = _re.findall(r'href=["\']([^"\']+\.mp4)["\']', html2)
            if not mp4_matches:
                mp4_matches = _re.findall(r'href=["\']([^"\']+\.mkv)["\']', html2)

            if not mp4_matches:
                browser.close()
                return None, None, None

            mp4_url = mp4_matches[0]

            # Step 5: Get all cookies from the browser context
            cookies = context.cookies()
            cookie_str = '; '.join(f"{c['name']}={c['value']}" for c in cookies)

            browser.close()
            return mp4_url, download_url, cookie_str

        except Exception as e:
            browser.close()
            return None, None, str(e)


def _playwright_stream_video(link_id_url: str, range_header: str = None):
    """
    Full Playwright flow: resolve the URL with browser JS, then download
    the video using the browser's cookies in a requests session.
    Returns (response, info_dict) or (None, None).
    """
    import requests as _req

    mp4_url, referer_url, cookie_str = _playwright_get_video_url(link_id_url)
    if not mp4_url:
        return None, None

    # Use requests with the exact cookies from the browser session
    session = _req.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
        'Referer': referer_url,
        'Accept': '*/*',
        'Cookie': cookie_str,
    }
    if range_header:
        headers['Range'] = range_header

    try:
        resp = session.get(mp4_url, headers=headers, stream=True, timeout=(15, 300))
        info = {
            'status_code': resp.status_code,
            'content_type': resp.headers.get('content-type', 'video/mp4'),
            'content_length': resp.headers.get('content-length'),
            'content_range': resp.headers.get('content-range'),
            'accept_ranges': resp.headers.get('accept-ranges', 'bytes'),
        }
        return resp, info
    except Exception:
        return None, None


def _fast_resolve_video_url(link_id: str):
    """Resolve an Akwam link to a direct CDN MP4 URL using plain HTTP requests.

    Uses the same approach as the original main.py CLI tool:
      1. GET /link/{id}  → parse /download/ URLs
      2. GET /download/… → parse direct CDN file URL from HTML

    The MP4 URL is already present in the raw HTML source — no JavaScript
    execution or Playwright browser needed.  This resolves in ~2s vs ~10s.

    Returns (mp4_url, download_page_url) or (None, None).
    """
    import re as _re
    import requests as _req

    HTTP = 'https://'
    RGX_SHORTEN = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
    RGX_DIRECT  = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        # Step 1: GET the /link/ page
        r1 = _req.get(f'{HTTP}go.akwam.com.co/link/{link_id}',
                       headers=HEADERS, timeout=30)
        shorten = _re.findall(RGX_SHORTEN, r1.content.decode('utf-8', errors='replace'))
        if not shorten:
            return None, None

        # Step 2: GET the download page
        dl_url = HTTP + shorten[0]
        r2 = _req.get(dl_url, headers=HEADERS, timeout=30)
        # Handle redirect (as main.py does)
        if dl_url != r2.url:
            r2 = _req.get(r2.url, headers=HEADERS, timeout=30)

        html = r2.content.decode('utf-8', errors='replace')

        # Step 3: Extract the CDN file URL (filter out self-referencing akwam links)
        all_matches = _re.findall(RGX_DIRECT, html)
        cdn_urls = [m for m in all_matches
                    if 'downet.net' in m or m.endswith('.mp4') or m.endswith('.mkv')]

        if cdn_urls:
            return HTTP + cdn_urls[0], dl_url

        # Fallback: try href-based patterns for .mp4/.mkv
        mp4 = _re.findall(r'href=["\']([^"\']+\.mp4)["\']', html)
        if mp4:
            return mp4[0], dl_url
        mkv = _re.findall(r'href=["\']([^"\']+\.mkv)["\']', html)
        if mkv:
            return mkv[0], dl_url

        return None, None
    except Exception:
        return None, None


@app.get("/api/akwam-resolve-stream")
async def akwam_resolve_stream(link_id: str):
    """Resolve an Akwam download link to a direct MP4 URL.

    Uses fast HTTP-only resolution (~2s) adapted from the original CLI tool.
    The CDN blocks datacenter IPs from downloading, but the URL extraction
    works fine — the user's own browser opens the URL directly.
    """
    if not link_id:
        raise HTTPException(status_code=400, detail="Missing 'link_id'")

    # Normalise: accept both "143994" and "go.akwam.com.co/link/143994"
    import re as _re_norm
    id_match = _re_norm.search(r'(\d+)$', link_id)
    if not id_match:
        raise HTTPException(status_code=400, detail="Invalid link_id format")
    numeric_id = id_match.group(1)

    loop = asyncio.get_event_loop()

    # Try fast HTTP resolution first (~2s)
    mp4_url, referer = await loop.run_in_executor(
        None, _fast_resolve_video_url, numeric_id
    )

    # Fallback to Playwright if fast method fails
    if not mp4_url:
        mp4_url, referer, _ = await loop.run_in_executor(
            None, _playwright_get_video_url, f"go.akwam.com.co/link/{numeric_id}"
        )

    if not mp4_url:
        raise HTTPException(
            status_code=502,
            detail="Could not resolve a streamable URL from Akwam"
        )

    return {"url": mp4_url, "referer": referer}


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
        result = await video_resolver.resolve(req.url)
        if not result:
            raise HTTPException(
                status_code=502, 
                detail="Could not resolve video URL from embed"
            )
        
        return {
            "url": result.url,
            "title": result.title,
            "ext": result.ext,
            "quality": result.quality,
            "filesize": result.filesize,
            "formats": result.formats,
        }
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
            async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
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
async def proxy_stream(url: str, request: Request):
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': url,
        'Accept': '*/*',
    }
    if range_header:
        headers['Range'] = range_header

    try:
        client = httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30.0, read=120.0))

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
            'Cache-Control': 'public, max-age=3600',
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
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
