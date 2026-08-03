import asyncio
from pathlib import Path

from starlette.requests import Request
from starlette.responses import StreamingResponse
from fastapi import HTTPException

import api.index as api_index
import api.browser_extractor as browser_extractor
from api.video_resolver import ResolvedVideo, VideoResolver


def check_player_modal_teardown():
    source = Path(__file__).with_name("app.js").read_text(encoding="utf-8")
    assert "function teardownPlayerContent(root = dom.mainModal)" in source
    assert "root.querySelectorAll('.embed-frame-wrap')" in source
    assert "wrap._resolveController.abort()" in source
    assert "root.querySelectorAll('video').forEach(teardownPlayerVideo)" in source
    assert "video._hls.destroy()" in source
    assert "teardownPlayerContent(dom.modalList);\n    dom.modalTitle.innerText = title;" in source
    assert "teardownPlayerContent(dom.mainModal);" in source


def check_provider_referers_reach_direct_player():
    source = Path(__file__).with_name("app.js").read_text(encoding="utf-8")
    assert 'data-referer="${escapeHtml(referer)}"' in source
    assert "const referer = safeRemoteUrl(button.dataset.referer);" in source
    assert "JSON.stringify({ url: embedUrl, referer: referer || null })" in source
    assert "resolveBtn.dataset.referer = safeRemoteUrl(btn.dataset.referer);" in source
    for frame_id in (
        "egyDeadFrame", "faselhdFrame", "wecimaFrame",
        "sahid4uFrame", "royaldramaFrame",
    ):
        assert f"renderPlayerFrame('{frame_id}'" in source
    assert source.count('data-referer="${escapeHtml(item.url)}"') >= 4
    assert 'data-referer="${escapeHtml(ep.url)}"' in source
    assert 'data-referer="${escapeHtml(url)}"' in source


def check_hls_rewrite():
    playlist = """#EXTM3U
#EXT-X-KEY:METHOD=AES-128,URI="key.bin"
#EXT-X-MAP:URI="init.mp4"
segment.ts
"""
    rewritten = api_index._rewrite_hls_to(
        playlist,
        "https://cdn.example/media/master.m3u8",
        lambda url: f"/proxy?url={url}",
    )
    assert 'URI="/proxy?url=https://cdn.example/media/key.bin"' in rewritten
    assert 'URI="/proxy?url=https://cdn.example/media/init.mp4"' in rewritten
    assert "/proxy?url=https://cdn.example/media/segment.ts" in rewritten


def check_manifest_candidate_prefers_stable_variants():
    signed_bootstrap = (
        "https://cdn.example/hls2/01/video.urlset/master.m3u8?t=signed"
    )
    stable_player_manifest = (
        "https://cdn.example/player/hls3/01/video.urlset/master.txt"
    )
    assert browser_extractor._manifest_candidate_score(
        stable_player_manifest
    ) > browser_extractor._manifest_candidate_score(signed_bootstrap)


def check_hls_proxy_uses_redirected_player_origin():
    async def run():
        original_capture = browser_extractor.capture_hls_manifest
        browser_extractor.capture_hls_manifest = lambda *args, **kwargs: (
            "https://player.example/stream/master.m3u8",
            "#EXTM3U\nvariant.m3u8\n",
            "https://player.example/embed/1",
        )
        try:
            response = await api_index.hls_proxy("https://alias.example/embed/1")
            body = response.body.decode()
            assert "ref=https%3A%2F%2Fplayer.example%2Fembed%2F1" in body
            assert "alias.example" not in body
        finally:
            browser_extractor.capture_hls_manifest = original_capture

    asyncio.run(run())


def check_hls_proxy_preserves_browser_session():
    async def run():
        original_capture = browser_extractor.capture_hls_manifest
        browser_extractor.capture_hls_manifest = lambda *args, **kwargs: (
            "https://cdn.example/stream/master.m3u8",
            "#EXTM3U\nvariant.m3u8\n",
            "https://player.example/embed/1",
            [{"name": "gate", "value": "ok", "domain": "cdn.example"}],
        )
        try:
            response = await api_index.hls_proxy("https://alias.example/embed/1")
            body = response.body.decode()
            assert "/api/media-proxy?sid=" in body
            sid = body.split("sid=", 1)[1].split("&", 1)[0]
            assert api_index.SESSION_STORE[sid]["referer"] == "https://player.example/embed/1"
            api_index.SESSION_STORE.pop(sid, None)
        finally:
            browser_extractor.capture_hls_manifest = original_capture

    asyncio.run(run())


def check_akwam_stream_rejects_lookalike_hosts():
    async def run():
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
        try:
            await api_index.akwam_stream("https://akwam.attacker.com/watch/1", request)
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("Akwam lookalike host was accepted")

    asyncio.run(run())


def check_akwam_stream_preserves_range_errors():
    class FalseyUpstream:
        def __bool__(self):
            return False

        def iter_content(self, chunk_size):
            return iter((b"range not satisfiable",))

        def close(self):
            pass

    async def run():
        original_stream_video = api_index.akwam.stream_video
        api_index.akwam.stream_video = lambda *args: (
            FalseyUpstream(),
            {
                "status_code": 416,
                "content_type": "video/mp4",
                "content_length": "21",
                "content_range": "bytes */1000",
                "accept_ranges": "bytes",
            },
        )
        try:
            request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
            response = await api_index.akwam_stream(
                "https://akwam.it/watch/1", request)
            assert isinstance(response, StreamingResponse)
            assert response.status_code == 416
            assert response.headers["content-range"] == "bytes */1000"
        finally:
            api_index.akwam.stream_video = original_stream_video

    asyncio.run(run())


def check_session_store_is_bounded():
    original_max = api_index.SESSION_MAX
    api_index.SESSION_STORE.clear()
    api_index.SESSION_MAX = 2
    try:
        api_index._store_session([], "https://one.example/", "https://one.example")
        api_index._store_session([], "https://two.example/", "https://two.example")
        api_index._store_session([], "https://three.example/", "https://three.example")
        assert len(api_index.SESSION_STORE) == 2
    finally:
        api_index.SESSION_MAX = original_max
        api_index.SESSION_STORE.clear()


def check_session_access_refreshes_expiry_and_lru():
    original_max = api_index.SESSION_MAX
    original_ttl = api_index.SESSION_TTL
    original_time = api_index.time.time
    api_index.SESSION_STORE.clear()
    api_index.SESSION_MAX = 2
    api_index.SESSION_TTL = 10
    now = iter((100, 101, 105, 106, 114))
    api_index.time.time = lambda: next(now)
    try:
        active_sid = api_index._store_session(
            [], "https://active.example/", "https://active.example")
        idle_sid = api_index._store_session(
            [], "https://idle.example/", "https://idle.example")

        assert api_index._get_session(active_sid) is not None
        assert api_index.SESSION_STORE[active_sid]["ts"] == 105

        replacement_sid = api_index._store_session(
            [], "https://new.example/", "https://new.example")
        assert active_sid in api_index.SESSION_STORE
        assert idle_sid not in api_index.SESSION_STORE
        assert replacement_sid in api_index.SESSION_STORE

        # This is beyond the original creation-time TTL but still within the
        # refreshed last-access TTL.
        assert api_index._get_session(active_sid) is not None
        assert api_index.SESSION_STORE[active_sid]["ts"] == 114
    finally:
        api_index.time.time = original_time
        api_index.SESSION_MAX = original_max
        api_index.SESSION_TTL = original_ttl
        api_index.SESSION_STORE.clear()


def check_resolver_cache_is_short_and_session_safe():
    class CountingResolver(VideoResolver):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def _resolve_sync(self, embed_url, cookies=None, referer=None):
            self.calls += 1
            return ResolvedVideo(url=f"https://cdn.example/video-{self.calls}.mp4")

    async def run():
        resolver = CountingResolver()
        first = await resolver.resolve("https://player.example/embed/1")
        second = await resolver.resolve("https://player.example/embed/1")
        assert first.url == second.url
        assert resolver.calls == 1

        await resolver.resolve(
            "https://player.example/embed/1",
            cookies=[{"name": "session", "value": "a"}],
            referer="https://partner.example/watch/1",
        )
        await resolver.resolve(
            "https://player.example/embed/1",
            cookies=[{"name": "session", "value": "b"}],
            referer="https://partner.example/watch/1",
        )
        assert resolver.calls == 3

    asyncio.run(run())


def check_generic_scraper_rejects_ad_urls():
    resolver = VideoResolver()
    ad_only = '<script>var url = "https://crn77.com/4/10225487";</script>'
    assert resolver._scrape_html_for_video(
        ad_only, "https://player.example/embed/1") is None

    manifest = '<script>const player = {"file": "https://cdn.example/path/master.txt"};</script>'
    result = resolver._scrape_html_for_video(
        manifest, "https://player.example/embed/1")
    assert result and result.ext == "m3u8"


def check_resolve_embed_returns_playable_proxy_urls():
    async def run():
        original_resolve = api_index.video_resolver.resolve

        async def direct_result(*args, **kwargs):
            return ResolvedVideo(url="https://cdn.example/video.mp4", ext="mp4")

        async def hls_result(*args, **kwargs):
            return ResolvedVideo(url="https://cdn.example/master.m3u8", ext="m3u8")

        try:
            api_index.video_resolver.resolve = direct_result
            direct = await api_index.resolve_embed(api_index.ResolveEmbedRequest(
                url="https://player.example/embed/1",
                referer="https://partner.example/watch/1",
            ))
            assert direct["proxy_url"].startswith("/api/proxy-stream?")
            assert "referer=https%3A%2F%2Fplayer.example%2F" in direct["proxy_url"]

            api_index.video_resolver.resolve = hls_result
            hls = await api_index.resolve_embed(api_index.ResolveEmbedRequest(
                url="https://hgcloud.to/e/1",
                referer="https://wecima.cx/watch/example",
            ))
            assert hls["proxy_url"].startswith("/api/hls-proxy?")
            assert "referer=https%3A%2F%2Fwecima.cx%2Fwatch%2Fexample" in hls["proxy_url"]
        finally:
            api_index.video_resolver.resolve = original_resolve

    asyncio.run(run())


def check_resolve_embed_uses_fast_govid_extractor():
    async def run():
        original_specific = api_index.faselhd.resolve_govid_embed
        original_generic = api_index.video_resolver.resolve

        def specific_result(url, post_id):
            return {"url": "https://cdn.example/token/master.m3u8", "type": "hls"}

        async def generic_must_not_run(*args, **kwargs):
            raise AssertionError("generic resolver should not run for resolved Govid HLS")

        api_index.faselhd.resolve_govid_embed = specific_result
        api_index.video_resolver.resolve = generic_must_not_run
        try:
            result = await api_index.resolve_embed(api_index.ResolveEmbedRequest(
                url="https://govid.live/play/123/",
            ))
            assert result["url"].endswith("master.m3u8")
            assert result["proxy_url"].startswith("/api/hls-seg?")
        finally:
            api_index.faselhd.resolve_govid_embed = original_specific
            api_index.video_resolver.resolve = original_generic

    asyncio.run(run())


def check_hls_segment_preserves_range():
    captured = {}

    class FakeResponse:
        status_code = 206
        content = b"segment"
        headers = {
            "content-type": "video/mp2t",
            "content-length": "7",
            "content-range": "bytes 2-8/20",
            "accept-ranges": "bytes",
        }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, headers=None):
            captured.update(url=url, headers=headers)
            return FakeResponse()

    async def run():
        original_client = api_index.httpx.AsyncClient
        api_index.httpx.AsyncClient = FakeClient
        try:
            request = Request({
                "type": "http",
                "method": "GET",
                "path": "/api/hls-seg",
                "headers": [(b"range", b"bytes=2-8")],
            })
            response = await api_index.hls_segment(
                "https://cdn.example/segment.ts",
                request,
                "https://player.example/embed/1",
            )
            assert response.status_code == 206
            assert response.body == b"segment"
            assert response.headers["content-range"] == "bytes 2-8/20"
            assert response.headers["content-length"] == "7"
            assert captured["headers"]["Range"] == "bytes=2-8"
            assert captured["headers"]["Referer"] == "https://player.example/embed/1"
            assert captured["headers"]["Origin"] == "https://player.example"
        finally:
            api_index.httpx.AsyncClient = original_client

    asyncio.run(run())


def check_media_proxy_streams_and_forwards_range():
    captured = {}

    class FakeResponse:
        status_code = 206
        headers = {
            "content-type": "video/mp4",
            "content-length": "6",
            "content-range": "bytes 2-7/20",
            "accept-ranges": "bytes",
        }

        async def aiter_bytes(self, chunk_size=65536):
            yield b"abc"
            yield b"def"

        async def aclose(self):
            captured["response_closed"] = True

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def build_request(self, method, url, headers=None, cookies=None):
            captured.update(method=method, url=url, headers=headers, cookies=cookies)
            return object()

        async def send(self, request, stream=False):
            captured["stream"] = stream
            return FakeResponse()

        async def aclose(self):
            captured["client_closed"] = True

    async def run():
        original_client = api_index.httpx.AsyncClient
        api_index.httpx.AsyncClient = FakeClient
        try:
            sid = api_index._store_session(
                [], "https://partner.example/watch/1", "https://player.example")
            request = Request({
                "type": "http",
                "method": "GET",
                "path": "/api/media-proxy",
                "headers": [(b"range", b"bytes=2-7")],
            })
            response = await api_index.media_proxy(
                sid, "https://cdn.example/video.urlset/seg-1.woff2", request)
            assert isinstance(response, StreamingResponse)
            assert response.status_code == 206
            body = b"".join([chunk async for chunk in response.body_iterator])
            assert body == b"abcdef"
            assert captured["stream"] is True
            assert captured["headers"]["Range"] == "bytes=2-7"
            assert captured["headers"]["Origin"] == "https://player.example"
            assert captured["headers"]["Accept-Language"] == "en-US,en;q=0.9"
            assert "Chrome/120.0.0.0" in captured["headers"]["User-Agent"]
            assert captured["response_closed"] and captured["client_closed"]
        finally:
            api_index.httpx.AsyncClient = original_client

    asyncio.run(run())


def run():
    check_player_modal_teardown()
    check_provider_referers_reach_direct_player()
    check_hls_rewrite()
    check_manifest_candidate_prefers_stable_variants()
    check_hls_proxy_uses_redirected_player_origin()
    check_hls_proxy_preserves_browser_session()
    check_akwam_stream_rejects_lookalike_hosts()
    check_akwam_stream_preserves_range_errors()
    check_session_store_is_bounded()
    check_session_access_refreshes_expiry_and_lru()
    check_resolver_cache_is_short_and_session_safe()
    check_generic_scraper_rejects_ad_urls()
    check_resolve_embed_returns_playable_proxy_urls()
    check_resolve_embed_uses_fast_govid_extractor()
    check_hls_segment_preserves_range()
    check_media_proxy_streams_and_forwards_range()
    print("playback regressions: ok")


if __name__ == "__main__":
    run()
