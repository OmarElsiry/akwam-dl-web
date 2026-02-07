from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
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
