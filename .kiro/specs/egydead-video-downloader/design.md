# EgyDead Video Downloader - Technical Design

## Overview

Add video downloading capability with ad-blocking for EgyDead embed servers (uqload, doodstream, streamtape, voe.sx, mixdrop, filemoon, etc.).

## High-Level Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (app.js)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Search    │  │   Browse    │  │  Download Button (NEW)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (index.py)                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  /api/egydead/watch         → Get embed URLs (existing)     ││
│  │  /api/egydead/download      → Download video file (NEW)     ││
│  │  /api/proxy-stream          → Stream without ads (existing) ││
│  │  /api/resolve-embed         → Extract direct URL (NEW)      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               Video Resolver Module (NEW)                        │
│                    (video_resolver.py)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  ││
│  │  │   yt-dlp    │  │  streamlink │  │  Custom extractors  │  ││
│  │  │  (primary)  │  │  (fallback) │  │  (Playwright-based) │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User clicks "Download" on video
2. Frontend calls /api/egydead/watch → gets embed URLs
3. Frontend calls /api/resolve-embed?url=<embed_url>
4. Backend resolves direct video URL using:
   a. yt-dlp (supports most embed hosts)
   b. streamlink (fallback for streaming sites)
   c. Custom Playwright scraper (last resort)
5. Backend returns direct video URL
6. User downloads via /api/proxy-stream (ad-free) or direct URL
```

### Ad-Blocking Strategy

The ad-blocking is achieved by **bypassing the embed page entirely**:

1. **Direct URL Extraction**: Extract the video URL without loading the ad-heavy embed page
2. **Server-Side Proxy**: Stream through `/api/proxy-stream` which:
   - Doesn't execute JavaScript (no popup ads)
   - Doesn't load ad scripts
   - Passes only the video stream to client

## Low-Level Design

### New File: `api/video_resolver.py`

```python
"""
Video URL resolver for embed players.
Uses yt-dlp as primary resolver with fallbacks.
"""

import asyncio
import re
from typing import Optional, Dict, List
from dataclasses import dataclass
import yt_dlp
import streamlink


@dataclass
class ResolvedVideo:
    """Result of resolving an embed URL."""
    url: str                    # Direct video URL
    title: Optional[str] = None
    ext: Optional[str] = None   # 'mp4', 'mkv', 'm3u8'
    quality: Optional[str] = None
    filesize: Optional[int] = None
    formats: Optional[List[Dict]] = None  # All available formats


class VideoResolver:
    """Resolves embed player URLs to direct video URLs."""

    # yt-dlp options for silent extraction
    YDL_OPTS = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'nocheckcertificate': True,
    }

    # Known embed hosts and their extraction methods
    EMBED_HOSTS = {
        'uqload': {'method': 'yt-dlp', 'pattern': r'uqload\.(com|io)'},
        'doodstream': {'method': 'yt-dlp', 'pattern': r'dood'},
        'streamtape': {'method': 'yt-dlp', 'pattern': r'streamtape'},
        'voe': {'method': 'yt-dlp', 'pattern': r'voe\.sx|voeun'},
        'mixdrop': {'method': 'yt-dlp', 'pattern': r'mixdrop'},
        'filemoon': {'method': 'yt-dlp', 'pattern': r'filemoon'},
        'vidoza': {'method': 'yt-dlp', 'pattern': r'vidoza'},
        'upstream': {'method': 'yt-dlp', 'pattern': r'upstream'},
        'streamlare': {'method': 'yt-dlp', 'pattern': r'streamlare'},
    }

    def __init__(self):
        self._cache: Dict[str, ResolvedVideo] = {}

    async def resolve(self, embed_url: str) -> Optional[ResolvedVideo]:
        """
        Resolve an embed URL to a direct video URL.
        
        Args:
            embed_url: URL from embed player (e.g., https://uqload.com/xyz)
            
        Returns:
            ResolvedVideo with direct URL, or None if resolution failed
        """
        # Check cache
        if embed_url in self._cache:
            return self._cache[embed_url]

        # Run resolution in thread pool (yt-dlp is blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._resolve_sync, embed_url)

        if result:
            self._cache[embed_url] = result
        return result

    def _resolve_sync(self, embed_url: str) -> Optional[ResolvedVideo]:
        """Synchronous resolution using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(self.YDL_OPTS) as ydl:
                info = ydl.extract_info(embed_url, download=False)
                
                if not info:
                    return None

                # Get best format
                formats = info.get('formats', [])
                best = self._select_best_format(formats)
                
                return ResolvedVideo(
                    url=best.get('url') if best else info.get('url'),
                    title=info.get('title'),
                    ext=info.get('ext', 'mp4'),
                    quality=self._get_quality_label(best) if best else None,
                    filesize=best.get('filesize') if best else None,
                    formats=[{'url': f['url'], 'ext': f.get('ext'), 
                              'quality': f.get('format_note', '')}
                             for f in formats if f.get('url')]
                )
        except Exception as e:
            print(f"[VideoResolver] yt-dlp failed: {e}")
            # Try fallback methods
            return self._fallback_resolve(embed_url)

    def _select_best_format(self, formats: List[Dict]) -> Optional[Dict]:
        """Select best quality format with video + audio."""
        # Prefer formats with both video and audio
        combined = [f for f in formats 
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
        if combined:
            return max(combined, key=lambda f: f.get('height', 0) or 0)
        
        # Fallback to any video format
        video = [f for f in formats if f.get('vcodec') != 'none']
        if video:
            return max(video, key=lambda f: f.get('height', 0) or 0)
        
        return formats[0] if formats else None

    def _get_quality_label(self, fmt: Dict) -> str:
        """Get human-readable quality label."""
        height = fmt.get('height', 0)
        if height >= 2160: return '4K'
        if height >= 1080: return '1080p'
        if height >= 720: return '720p'
        if height >= 480: return '480p'
        if height >= 360: return '360p'
        return fmt.get('format_note', 'Unknown')

    def _fallback_resolve(self, url: str) -> Optional[ResolvedVideo]:
        """Fallback resolution using streamlink or custom scraper."""
        # Try streamlink for streaming sites
        try:
            streams = streamlink.streams(url)
            if streams:
                best = streams.get('best') or streams.get('720p') or list(streams.values())[0]
                return ResolvedVideo(url=best.url, ext='m3u8')
        except Exception as e:
            print(f"[VideoResolver] streamlink failed: {e}")

        return None
```

### New API Endpoints in `api/index.py`

```python
# Add to imports
from .video_resolver import VideoResolver, ResolvedVideo

# Initialize resolver
video_resolver = VideoResolver()

class ResolveEmbedRequest(BaseModel):
    url: str
    quality: Optional[str] = None  # 'best', '1080p', '720p', '480p'

class DownloadRequest(BaseModel):
    url: str
    filename: Optional[str] = None

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
        from fastapi.responses import StreamingResponse
        import httpx

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
```

### Frontend Changes in `app.js`

```javascript
// Add download button to video player UI
async function downloadVideo(embedUrl, title) {
    try {
        showLoading('Resolving video...');
        
        // Step 1: Resolve the embed URL
        const resolveResp = await fetch('/api/resolve-embed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: embedUrl })
        });
        
        if (!resolveResp.ok) throw new Error('Failed to resolve video');
        
        const resolved = await resolveResp.json();
        
        // Step 2: Trigger download via proxy (ad-free)
        const filename = `${title || 'video'}.${resolved.ext || 'mp4'}`;
        const proxyUrl = `/api/proxy-stream?url=${encodeURIComponent(resolved.url)}`;
        
        // Create download link
        const a = document.createElement('a');
        a.href = proxyUrl;
        a.download = filename;
        a.click();
        
        hideLoading();
    } catch (error) {
        hideLoading();
        showError('Download failed: ' + error.message);
    }
}
```

## Dependencies

Add to `requirements.txt`:
```
yt-dlp>=2024.0.0
streamlink>=6.0.0
```

## Implementation Notes

### Why yt-dlp?

- Supports **1000+ sites** including all major embed hosts
- Actively maintained with frequent updates
- Can be used as Python library
- Handles format selection automatically

### Ad-Blocking Mechanism

Ads in embed players work via:
1. JavaScript popups on page load
2. Overlay ads during video playback
3. Redirect chains before showing video

Our solution **bypasses all of this** by:
1. Extracting the direct video URL server-side
2. Streaming the raw video data without executing any JavaScript
3. No ad scripts ever load because we never load the embed page

### Supported Hosts

| Host | yt-dlp Support | Notes |
|------|---------------|-------|
| uqload | ✅ | Full support |
| doodstream | ✅ | Full support |
| streamtape | ✅ | Full support |
| voe.sx | ✅ | Full support |
| mixdrop | ✅ | Full support |
| filemoon | ✅ | Full support |
| vidoza | ✅ | Full support |
| upstream | ✅ | Full support |

## Tasks

1. Create `api/video_resolver.py` with yt-dlp integration
2. Add `/api/resolve-embed` endpoint to `api/index.py`
3. Add `/api/egydead/download` endpoint to `api/index.py`
4. Update `requirements.txt` with yt-dlp and streamlink
5. Update frontend `app.js` with download button and handlers
6. Add download UI to `index.html`
7. Test with various embed hosts
