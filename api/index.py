import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from .akwam_api import AkwamAPI
from .egydead_api import EgyDeadAPI
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

# ------------------------------------------------------------------ #
#  Shared models
# ------------------------------------------------------------------ #

class LinkRequest(BaseModel):
    url: str

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

class BulkResolveRequest(BaseModel):
    urls: List[Dict[str, str]] # List of {name: "...", url: "..."}

@app.post("/api/bulk-resolve")
async def bulk_resolve(req: BulkResolveRequest):
    try:
        loop = asyncio.get_event_loop()
        tasks = []
        for item in req.urls:
            tasks.append(loop.run_in_executor(None, akwam.get_qualities, item['url']))
        
        all_qualities = await asyncio.gather(*tasks)
        
        resolve_tasks = []
        episode_names = []
        for i, qualities in enumerate(all_qualities):
            best_q = next((q for q in qualities if q['quality'] == '720p'), None)
            if not best_q and qualities:
                best_q = qualities[0]
            
            if best_q:
                episode_names.append(req.urls[i]['name'])
                resolve_tasks.append(loop.run_in_executor(None, akwam.resolve_direct_url, best_q['link_id']))

        direct_urls = await asyncio.gather(*resolve_tasks)
        
        results = []
        for name, url in zip(episode_names, direct_urls):
            if url:
                results.append({"name": name, "url": url})
        
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
#  Health
# ------------------------------------------------------------------ #

@app.get("/api/health")
async def health():
    return {"status": "ok"}
