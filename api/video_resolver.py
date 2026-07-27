"""
Video URL resolver for embed players.
Uses yt-dlp as primary resolver with fallbacks.
"""

import asyncio
import re
import time
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

    # Resolver results are commonly signed, short-lived URLs.  A small cache
    # absorbs duplicate UI requests without serving an expired stream later.
    CACHE_TTL_SECONDS = 90

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
        self._cache: Dict[str, tuple[float, ResolvedVideo]] = {}

    async def resolve(self, embed_url: str, cookies: list = None,
                      referer: str = None) -> Optional[ResolvedVideo]:
        """
        Resolve an embed URL to a direct video URL.
        
        Args:
            embed_url: URL from embed player (e.g., https://uqload.com/xyz)
            
        Returns:
            ResolvedVideo with direct URL, or None if resolution failed
        """
        # Cookie/referer-backed resolutions are user-session-specific and must
        # never be shared through the process-wide cache.
        use_cache = not cookies and not referer
        if use_cache and embed_url in self._cache:
            cached_at, cached_result = self._cache[embed_url]
            if time.monotonic() - cached_at < self.CACHE_TTL_SECONDS:
                return cached_result
            self._cache.pop(embed_url, None)

        # Run resolution in thread pool (yt-dlp is blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._resolve_sync, embed_url, cookies, referer)

        if result and use_cache:
            self._cache[embed_url] = (time.monotonic(), result)
        return result

    # Known JS-only hosts — skip yt-dlp, go directly to Playwright
    _JS_ONLY_HOSTS = [
        'govid.live', 'govid.me', 'vidspeed.org', 'vidoba.org',
        'hglink.to', 'dhcplay.com', 'callistanise.com', 'dingtezuni.com', 'playmogo.com',
        'hgcloud.to',
        'miiiixdrop.net', 'fastvid.cam', 'fastved.cam', 'vinovo.to',
        'vipserver.liiivideo.com', 'lulustream.com', 'shaaheid4u.rpmvip.com',
        'doodstream.com', 'mixdrop.ps', 'mixdrop.top', 'vidtube.pro',
    ]

    def _is_js_only(self, url: str) -> bool:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        return any(d in host for d in self._JS_ONLY_HOSTS)

    def _resolve_sync(self, embed_url: str, cookies: list = None,
                      referer: str = None) -> Optional[ResolvedVideo]:
        """Synchronous resolution using yt-dlp."""
        # Skip yt-dlp for known JS-only hosts — go straight to fallback
        if self._is_js_only(embed_url):
            return self._fallback_resolve(embed_url, cookies=cookies, referer=referer)

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
            return self._fallback_resolve(
                embed_url, cookies=cookies, referer=referer)

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

    def _fallback_resolve(self, url: str, _depth: int = 0, cookies: list = None,
                          referer: str = None) -> Optional[ResolvedVideo]:
        """Fallback resolution using streamlink or generic scraping."""
        if _depth > 3:
            return None

        # Known JS-only hosts — skip intermediate fallbacks, go straight to Playwright
        if self._is_js_only(url):
            return self._browser_resolve(url, referer=referer, cookies=cookies, _depth=_depth)

        # Try streamlink for streaming sites
        try:
            import streamlink
            streams = streamlink.streams(url)
            if streams:
                best = streams.get('best') or streams.get('720p') or list(streams.values())[0]
                return ResolvedVideo(url=best.url, ext='m3u8')
        except ImportError:
            pass
        except Exception as e:
            print(f"[VideoResolver] streamlink failed: {e}")

        # Generic HTML scraper fallback
        try:
            import requests as _req
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/120.0.0.0 Safari/537.36',
                'Referer': url,
                'Accept': '*/*',
            }
            r = _req.get(url, headers=headers, timeout=15, allow_redirects=True)
            html = r.content.decode('utf-8', errors='replace')

            found = self._scrape_html_for_video(
                html, url, _depth, cookies=cookies, referer=referer)
            if found:
                return found
        except Exception as e:
            print(f"[VideoResolver] generic fallback failed: {e}")

        # ── File-host extractor (XFilesharing-style: LiiiVideo, etc.) ──
        try:
            fh = self._extract_file_host(url, timeout=20)
            if fh:
                return fh
        except Exception as e:
            print(f"[VideoResolver] file-host extract failed: {e}")

        # ── Last resort: headless browser (Playwright) ──────────
        return self._browser_resolve(url, referer=referer, cookies=cookies, _depth=_depth)

    def _browser_resolve(self, url: str, referer: str = None, cookies: list = None,
                         _depth: int = 0) -> Optional[ResolvedVideo]:
        try:
            from .browser_extractor import resolve_embed_via_browser
            video_url = resolve_embed_via_browser(
                url, referer=referer, cookies=cookies)
            if video_url:
                low = video_url.lower()
                ext = 'm3u8'
                if not ('.m3u8' in low or 'urlset' in low or 'master.txt' in low
                        or 'mpegurl' in low or low.endswith('.m3u')):
                    ext = 'mp4'
                return ResolvedVideo(url=video_url, ext=ext)
        except Exception as e:
            print(f"[VideoResolver] browser fallback failed: {e}")
        return None

    def _scrape_html_for_video(self, html: str, page_url: str, _depth: int = 0,
                               cookies: list = None,
                               referer: str = None) -> Optional[ResolvedVideo]:
        """Try many patterns to extract a video URL from HTML."""
        import re as _re

        # Helper to resolve relative URLs
        def _abs(u):
            if u and u.startswith('//'):
                return 'https:' + u
            if u and u.startswith('/'):
                from urllib.parse import urlparse
                parsed = urlparse(page_url)
                return f'{parsed.scheme}://{parsed.netloc}{u}'
            return u

        # Helper to check a URL candidate
        def _check_url(candidate):
            if not candidate:
                return None
            url = _abs(candidate.strip().strip('"').strip("'"))
            low = (url or '').lower()
            is_manifest = (
                '.m3u8' in low or 'master.txt' in low or 'urlset' in low
                or low.endswith('.m3u') or '/manifest' in low
            )
            is_video_file = any(
                ext in low for ext in ('.mp4', '.mkv', '.webm', '.m4v', '.mov')
            )
            if url and (is_video_file or is_manifest):
                ext = 'mp4'
                if is_manifest: ext = 'm3u8'
                if '.mkv' in low: ext = 'mkv'
                if '.webm' in low: ext = 'webm'
                return ResolvedVideo(url=url, ext=ext)
            return None

        # ── Pattern 1: <source> tags ──────────────────────────────
        for src_tag in _re.finditer(
            r'<source\s+[^>]*src=["\']([^"\']+)["\']',
            html, _re.IGNORECASE
        ):
            result = _check_url(src_tag.group(1))
            if result:
                return result

        # ── Pattern 2: <video> tag with src ───────────────────────
        for vid in _re.finditer(
            r'<video[^>]*src=["\']([^"\']+)["\']',
            html, _re.IGNORECASE
        ):
            result = _check_url(vid.group(1))
            if result:
                return result

        # ── Pattern 3: <a href="...mp4" download> ─────────────────
        for a_tag in _re.finditer(
            r'href=["\']([^"\']+\.(?:mp4|mkv|m3u8|webm))["\'][^>]*download',
            html, _re.IGNORECASE
        ):
            result = _check_url(a_tag.group(1))
            if result:
                return result

        # ── Pattern 4: any <a href="...mp4"> ──────────────────────
        for a_tag in _re.finditer(
            r'href=["\']([^"\']+\.(?:mp4|mkv|m3u8|webm))["\']',
            html, _re.IGNORECASE
        ):
            result = _check_url(a_tag.group(1))
            if result:
                return result

        # ── Pattern 5: JS variables (file, src, url, source, video) ──
        for var_name in ['file', 'src', 'url', 'source', 'video', 'link', 'mp4', 'u']:
            # "var_name": "value" or 'var_name': 'value'
            for m in _re.finditer(
                rf'''["']{var_name}["']\s*(?::|=)\s*["']([^"']+)["']''',
                html
            ):
                result = _check_url(m.group(1))
                if result:
                    return result

        # ── Pattern 6: JS sources array ───────────────────────────
        # sources: [{file: "..."}, ...] or playlist: [{file: "..."}, ...]
        for array_var in ['sources', 'playlist', 'files']:
            for m in _re.finditer(
                rf'''["']{array_var}["']\s*:\s*\[([\s\S]*?)\]''',
                html
            ):
                for file_m in _re.finditer(
                    r'''["']file["']\s*:\s*["']([^"']+)["']''',
                    m.group(1)
                ):
                    result = _check_url(file_m.group(1))
                    if result:
                        return result

        # ── Pattern 7: data-src ───────────────────────────────────
        for ds in _re.finditer(
            r'data-src=["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
            html, _re.IGNORECASE
        ):
            result = _check_url(ds.group(1))
            if result:
                return result

        # ── Pattern 8: data-video / data-file / data-url ──────────
        for attr in ['data-video', 'data-file', 'data-url', 'data-href']:
            for m in _re.finditer(
                rf'{attr}=["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
                html, _re.IGNORECASE
            ):
                result = _check_url(m.group(1))
                if result:
                    return result

        # ── Pattern 9: direct URL in plain text (unquoted .mp4 URLs) ──
        for m in _re.finditer(
            r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*)',
            html
        ):
            result = _check_url(m.group(1))
            if result:
                return result

        # ── Pattern 10: base64-encoded video URLs in JS ───────────
        # Some sites encode URLs like window.atob("base64...")
        for m in _re.finditer(
            r'(?:atob|b64_decode)\s*\(\s*["\']([A-Za-z0-9+/=]{20,})["\']',
            html
        ):
            try:
                import base64
                decoded = base64.b64decode(m.group(1)).decode('utf-8')
                result = _check_url(decoded)
                if result:
                    return result
            except Exception:
                pass

        # ── Pattern 11: hex-encoded strings (like \x68\x74\x74\x70) ──
        for m in _re.finditer(
            r'(?:\\x[0-9a-fA-F]{2}){10,}',
            html
        ):
            try:
                decoded = m.group(0).encode('utf-8').decode('unicode_escape')
                result = _check_url(decoded)
                if result:
                    return result
            except Exception:
                pass

        # ── Pattern 12: iframe src — recurse ──────────────────────
        for m in _re.finditer(
            r'<iframe[^>]*src=["\'](https?://[^"\']+)["\']',
            html, _re.IGNORECASE
        ):
            iframe_url = m.group(1)
            if iframe_url != page_url and not iframe_url.startswith('javascript'):
                result = self._fallback_resolve(
                    iframe_url, _depth + 1, cookies=cookies,
                    referer=referer or page_url)
                if result:
                    return result

        # ── Pattern 13: embed tag src ─────────────────────────────
        for m in _re.finditer(
            r'<embed[^>]*src=["\']([^"\']+)["\']',
            html, _re.IGNORECASE
        ):
            result = _check_url(m.group(1))
            if result:
                return result

        # ── Pattern 14: JW Player-style setup ─────────────────────
        for m in _re.finditer(
            r'setup\s*\(\s*\{([\s\S]*?)\}\s*\)',
            html
        ):
            for fm in _re.finditer(
                r'''["']file["']\s*:\s*["']([^"']+)["']''',
                m.group(1)
            ):
                result = _check_url(fm.group(1))
                if result:
                    return result

        return None

    # ------------------------------------------------------------------ #
    #  File-host extractor (XFilesharing-style: LiiiVideo / vipserver etc.)
    # ------------------------------------------------------------------ #

    def _extract_file_host(self, url: str, timeout: int = 20) -> Optional[ResolvedVideo]:
        """Extract a direct video file URL from an XFilesharing-style file host
        (e.g. vipserver.liiivideo.com / "LiiiVideo"). The embed page shows a
        download form; POSTing it reveals a signed, time-limited direct file
        URL (often on a random CDN subdomain). No browser required.
        """
        import re as _re
        import requests as _req
        from urllib.parse import urlparse, urljoin

        try:
            session = _req.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': url,
            }

            r = session.get(url, headers=headers, timeout=timeout)
            html = r.content.decode('utf-8', 'replace')

            has_form = ('id="F1"' in html or
                        _re.search(r'name=["\']op["\'][^>]*value=["\']download', html) is not None)

            # Collect candidate download pages: the page itself (if it has a
            # form) plus any /d/<id>_<q> quality links.
            ordered = []
            if has_form:
                ordered.append(url)
            quals = []
            for m in _re.finditer(r'href=["\']([^"\']*/(?:d|download)/[^"\']+)["\']', html):
                c = m.group(1)
                if c.startswith('/'):
                    p = urlparse(url)
                    c = f'{p.scheme}://{p.netloc}{c}'
                quals.append(c)
            quals = list(dict.fromkeys(quals))
            quals.sort(key=lambda u: (0 if '_h' in u else (1 if '_n' in u else 2)))
            ordered += quals

            for cand in ordered:
                res = self._post_file_form(session, cand, url, headers, timeout)
                if res:
                    return res
        except Exception as e:
            print(f"[VideoResolver] file-host extract failed: {e}")
        return None

    @staticmethod
    def _post_file_form(session, form_url, ref_url, headers, timeout):
        """GET a download page, POST its hidden form fields, and parse the
        resulting direct video file URL."""
        import re as _re
        import time as _time
        from urllib.parse import urlparse

        try:
            r = session.get(form_url, headers={**headers, 'Referer': ref_url}, timeout=timeout)
            html = r.content.decode('utf-8', 'replace')

            fields = {}
            for m in _re.finditer(r'<input[^>]*>', html):
                tag = m.group(0)
                nm = _re.search(r'name=["\']([^"\']+)["\']', tag)
                vl = _re.search(r'value=["\']([^"\']*)["\']', tag)
                if nm and vl:
                    fields[nm.group(1)] = vl.group(1)
            if 'op' not in fields:
                return None

            fm = _re.search(r'<form[^>]*action=["\']([^"\']*)["\']', html)
            action = fm.group(1) if fm else form_url
            if not action or action.startswith('#'):
                action = form_url
            elif action.startswith('/'):
                p = urlparse(form_url)
                action = f'{p.scheme}://{p.netloc}{action}'

            # XFilesharing anti-bot: the form hash is only honoured after a
            # short cooldown since the page was loaded, so wait before POSTing.
            _time.sleep(6)

            resp = session.post(
                action, data=fields,
                headers={**headers, 'Referer': form_url},
                timeout=timeout, allow_redirects=True,
            )
            body = resp.content.decode('utf-8', 'replace')

            dm = _re.search(
                r'href=["\'](https?://[^"\']+\.(?:mp4|mkv|webm|ts)(?:\?[^"\']*)?)["\']',
                body,
            )
            if dm:
                return ResolvedVideo(url=dm.group(1), ext='mp4')
            return None
        except Exception:
            return None
