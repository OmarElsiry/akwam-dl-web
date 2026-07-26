from api.egydead_api import EgyDeadAPI
from api.index import app
from api.royaldrama_api import _parse_grid


def run():
    html = '''
    <a href="https://tv10.egydead.live/category/english-movies/">Movies</a>
    <li class="movieItem"><a href="https://tv10.egydead.live/inception/">
      <img src="poster.jpg"></a></li>
    '''
    markdown = '''
    [Movies](https://tv10.egydead.live/category/english-movies/ "Movies")
    [Inception](https://tv10.egydead.live/inception/ "Inception")
    '''
    results = EgyDeadAPI()._parse_search_results(markdown, html)
    assert [item['name'] for item in results] == ['Inception']

    html = '''
    <li class="movieItem"><a href="https://tv10.egydead.live/serie/show/">
      <img src="poster.jpg"></a></li>
    '''
    markdown = '[Show](https://tv10.egydead.live/serie/show/ "Show")'
    assert EgyDeadAPI()._parse_search_results(markdown, html)[0]['type'] == 'series'

    trailer = '<iframe src="https://www.youtube.com/embed/trailer"></iframe>'
    assert EgyDeadAPI()._extract_from_html(trailer)[0] == []

    royal = '''
    <li class="col-md-3">
      <a title="Watch Later" href="#login">Later</a>
      <a href="/watch.php?vid=1&amp;part=2" title="مسلسل ما الحلقة 3">
      <img src="/poster.webp"></a></li>
    '''
    royal_item = _parse_grid(royal)[0]
    assert royal_item['type'] == 'episode'
    assert royal_item['url'].endswith('/watch.php?vid=1&part=2')

    title_first = '''
    <li class="col-md-3"><a title="A Movie" href="/watch.php?vid=2">
      <img src="/poster.webp"></a></li>
    '''
    assert _parse_grid(title_first)[0]['name'] == 'A Movie'

    sahid_paths = [route.path for route in app.routes if route.path.startswith('/api/sahid4u/')]
    assert len(sahid_paths) == len(set(sahid_paths))

    with open('app.js', encoding='utf-8') as source:
        player_source = source.read()
    assert player_source.count('<iframe') == 1
    assert 'sandbox="allow-scripts allow-same-origin allow-presentation"' in player_source

    print('provider regressions: ok')


if __name__ == '__main__':
    run()
