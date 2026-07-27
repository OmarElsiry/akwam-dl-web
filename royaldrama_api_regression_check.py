from api.royaldrama_api import (
    _abs,
    _clean_url,
    _normalize_server_url,
    _parse_grid,
    get_detail,
)


def test_translate_urls_are_cleaned():
    url = (
        "https://w9.royal-drama.com/watch.php?vid=abc123"
        "&amp;_x_tr_sl=auto&amp;_x_tr_tl=ar&amp;_x_tr_hl"
    )
    assert _clean_url(url) == "https://w9.royal-drama.com/watch.php?vid=abc123"
    assert _abs(url) == "https://w9.royal-drama.com/watch.php?vid=abc123"


def test_episode_grid_type_and_clean_url():
    page = '''
    <li class="col-xs-6 col-md-3">
      <a href="https://w9.royal-drama.com/watch.php?vid=ep1&amp;_x_tr_tl=ar"
         title="الحلقة 1"><img src="/poster.webp"></a>
    </li>
    '''
    item = _parse_grid(page, force_type="episode")[0]
    assert item["type"] == "episode"
    assert item["url"] == "https://w9.royal-drama.com/watch.php?vid=ep1"


def test_uqload_bz_embed_keeps_id_on_working_mirror():
    assert _normalize_server_url(
        "https://uqload.bz/embed-1dhhibliz1p3.html"
    ) == "https://uqload.is/embed-1dhhibliz1p3.html"


def test_detail_extracts_all_unique_servers(monkeypatch):
    watch = '<meta property="og:title" content="Movie">'
    view = '''
      <li data-embed="&lt;iframe src='https://vid.example/e/one'&gt;&lt;/iframe&gt;">
        <a><strong>One</strong></a>
      </li>
      <li data-embed="&lt;iframe src='https://vid.example/e/one'&gt;&lt;/iframe&gt;">
        <a><strong>Duplicate</strong></a>
      </li>
      <li data-embed="&lt;iframe src='https://other.example/e/two'&gt;&lt;/iframe&gt;">
        <a><strong>Two</strong></a>
      </li>
    '''
    monkeypatch.setattr(
        "api.royaldrama_api._fetch",
        lambda url, timeout=30: view if "view.php" in url else watch,
    )
    servers = get_detail("https://w9.royal-drama.com/watch.php?vid=movie")["servers"]
    assert servers == [
        {"name": "One", "url": "https://vid.example/e/one"},
        {"name": "Two", "url": "https://other.example/e/two"},
    ]
