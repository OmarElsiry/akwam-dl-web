import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from .akwam_api import AkwamAPI
from .egydead_api import EgyDeadAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

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
#  Health
# ------------------------------------------------------------------ #

@app.get("/api/health")
async def health():
    return {"status": "ok"}
