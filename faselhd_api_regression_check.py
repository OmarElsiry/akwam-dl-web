"""Focused regression checks for FaselHD's govid player resolver."""

import asyncio
from unittest.mock import patch

from api.faselhd_api import FaselhdAPI
import api.index as api_index


class FakeResponse:
    def __init__(self, text, ok=True):
        self.text = text
        self.ok = ok


def run():
    media_url = "https://govid.live/video-218062.m3u8?token=short-lived"
    encoded = media_url.encode().hex()

    def fake_get(url, **_kwargs):
        if "/play/" in url:
            return FakeResponse('<iframe src="https://govid.live/e/218062/"></iframe>')
        if "/e/218062/" in url:
            return FakeResponse(f'<script>const RenamedToken = "{encoded}";</script>')
        if "/d/218062/" in url:
            return FakeResponse("<html>download</html>")
        raise AssertionError(f"unexpected URL: {url}")

    api = FaselhdAPI()
    with patch("api.faselhd_api.safe_get", side_effect=fake_get):
        play = api.resolve_govid_embed("https://govid.live/play/opaque/", None)
        download = api.resolve_govid_embed("https://govid.live/d/218062/", None)

    assert play == {"url": media_url, "type": "hls"}, play
    assert download == {"url": media_url, "type": "hls"}, download

    async def check_servers_endpoint_uses_post_page_lookup():
        expected = [{"name": "Server 1", "embed_url": "https://govid.live/play/1/"}]
        with patch.object(
            api_index.faselhd,
            "get_post_detail",
            return_value={"servers": expected},
        ) as detail_lookup:
            response = await api_index.faselhd_get_servers(432690)
        detail_lookup.assert_called_once_with(432690)
        assert response == {"servers": expected}, response

    asyncio.run(check_servers_endpoint_uses_post_page_lookup())
    print("FaselHD govid resolver regression checks passed")


if __name__ == "__main__":
    run()
