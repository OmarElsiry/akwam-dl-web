import asyncio
from pydantic import BaseModel
from typing import Optional, List, Dict
from .akwam_api import AkwamAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse, FileResponse
import os

app = FastAPI(title="Akwam DL API")

@app.get("/", response_class=FileResponse)
async def read_root():
    return os.path.join(os.path.dirname(__file__), "..", "index.html")

@app.get("/style.css")
async def get_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "style.css"))

@app.get("/app.js")
async def get_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "app.js"))


# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

akwam = AkwamAPI()

class SearchQuery(BaseModel):
    q: str
    type: str = "movie"

class LinkRequest(BaseModel):
    url: str

@app.get("/api/search")
async def search(q: str, type: str = "movie"):
    try:
        results = akwam.search(q, type)
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

class BulkResolveRequest(BaseModel):
    urls: List[Dict[str, str]] # List of {name: "...", url: "..."}

@app.post("/api/bulk-resolve")
async def bulk_resolve(req: BulkResolveRequest):
    try:
        # Use concurrent threads for resolution since it's I/O bound (network requests)
        loop = asyncio.get_event_loop()
        tasks = []
        for item in req.urls:
            tasks.append(loop.run_in_executor(None, akwam.get_qualities, item['url']))
        
        # 1. Get qualities for all episodes
        all_qualities = await asyncio.gather(*tasks)
        
        # 2. Extract best quality (720p or first available) link_id for each
        resolve_tasks = []
        episode_names = []
        for i, qualities in enumerate(all_qualities):
            best_q = next((q for q in qualities if q['quality'] == '720p'), None)
            if not best_q and qualities:
                best_q = qualities[0]
            
            if best_q:
                episode_names.append(req.urls[i]['name'])
                resolve_tasks.append(loop.run_in_executor(None, akwam.resolve_direct_url, best_q['link_id']))

        # 3. Resolve all direct URLs
        direct_urls = await asyncio.gather(*resolve_tasks)
        
        results = []
        for name, url in zip(episode_names, direct_urls):
            if url:
                results.append({"name": name, "url": url})
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {"status": "ok"}
