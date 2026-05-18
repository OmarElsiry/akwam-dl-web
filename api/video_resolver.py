"""
Video URL resolver for embed players.
Uses yt-dlp as primary resolver with fallbacks.
"""

import asyncio
import re
from typing import Optional, Dict, List
from dataclasses import dataclass

import yt_dlp


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
            import streamlink
            streams = streamlink.streams(url)
            if streams:
                best = streams.get('best') or streams.get('720p') or list(streams.values())[0]
                return ResolvedVideo(url=best.url, ext='m3u8')
        except ImportError:
            print("[VideoResolver] streamlink not available for fallback")
        except Exception as e:
            print(f"[VideoResolver] streamlink failed: {e}")

        return None
