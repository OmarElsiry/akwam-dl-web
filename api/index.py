from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .akwam_api import AkwamAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse
import os

app = FastAPI(title="Akwam DL API")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Akwam-DL API</h1><p>Frontend file not found.</p>"


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

@app.post("/api/resolve")
async def resolve_url(req: LinkRequest):
    try:
        direct_url = akwam.resolve_direct_url(req.url)
        if not direct_url:
            raise HTTPException(status_code=404, detail="Could not resolve direct URL")
        return {"url": direct_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {"status": "ok"}
