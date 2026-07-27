from api.egydead_api import EgyDeadAPI


def run():
    api = EgyDeadAPI()

    html = '''
    <ul class="serversList">
      <li data-link="//player.example/e/abc?one=1&amp;two=2">
        <span><p>Mirror</p></span>
      </li>
    </ul>
    <ul class="donwload-servers-list">
      <li>
        <span class="ser-name">Direct</span>
        <div class="server-info"><em>1080p</em></div>
        <a href="/downloads/video.mp4.html">Download</a>
      </li>
    </ul>
    <script>const stream = "https://cdn.example/video.mp4?token=a&amp;b=2";</script>
    '''

    servers, downloads, direct_urls = api._extract_from_html(
        html, 'https://tv10.egydead.live/episode/sample/')

    assert servers == [{
        'name': 'Mirror',
        'url': 'https://player.example/e/abc?one=1&two=2',
    }]
    assert downloads == [{
        'name': 'Direct',
        'quality': '1080p',
        'url': 'https://tv10.egydead.live/downloads/video.mp4.html',
    }]
    assert direct_urls == ['https://cdn.example/video.mp4?token=a&b=2']

    landing_page = '<a href="https://files.example/movie.mp4.html">Download</a>'
    assert api._extract_from_html(landing_page)[2] == []

    navigation_markdown = '''
    [Seasons](https://egydead.com/season/ "Seasons")
    [Season 2](https://tv10.egydead.live/season/show-s02/ "Season 2")
    [Episodes](https://egydead.com/episode/ "Episodes")
    [Episode 1](https://tv10.egydead.live/episode/show-s02e01/ "Episode 1")
    '''
    assert api._parse_links_by_type(navigation_markdown, '/season/') == [{
        'name': 'Season 2',
        'url': 'https://tv10.egydead.live/season/show-s02/',
    }]
    assert api._parse_links_by_type(navigation_markdown, '/episode/') == [{
        'name': 'Episode 1',
        'url': 'https://tv10.egydead.live/episode/show-s02e01/',
    }]

    print('egydead provider regressions: ok')


if __name__ == '__main__':
    run()
