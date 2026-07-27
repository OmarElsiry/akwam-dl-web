from unittest.mock import patch

from api import sahid4u_api
from api.browser_extractor import PARTNER_REFERERS


def run():
    assert 'https://shhahhid4u.com/' in PARTNER_REFERERS
    assert sahid4u_api._is_challenge_page('<title>Just a moment...</title>')
    assert sahid4u_api._is_challenge_page('<title>Attention Required! | Cloudflare</title><div id="cf-error-details">')
    assert not sahid4u_api._is_challenge_page('<title>Real content</title>')
    assert not sahid4u_api._is_challenge_page(
        '<title>Real content</title><script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>'
    )

    class Response:
        status_code = 200
        text = '<a href="https://sahid4u.com/film/rock-roll"><h3>Rock & Roll</h3></a>'

    with patch('curl_cffi.requests.get', return_value=Response()) as request:
        results = sahid4u_api.search('rock & roll')
    assert request.call_args.args[0].endswith('/search?s=rock+%26+roll')
    assert results[0]['url'] == 'https://sahid4u.com/film/rock-roll'

    content_url = 'https://sahid4u.com/episode/example-episode'
    requested = []

    def fake_fetch(url, timeout=15):
        requested.append(url)
        if '/watch/' in url:
            return '''
                <script>
                let rawServers = [
                    {"name":"EarnVids","url":"https://fastvid.cam/embed/abc","id":1}
                ];
                </script>
            '''
        if '/download/' in url:
            return '<a href="/quality/720p" class="btn btn-gray">720p</a>'
        return '<title>Example episode</title>'

    with patch.object(sahid4u_api, '_fetch', side_effect=fake_fetch):
        data = sahid4u_api.get_content_servers_and_downloads(content_url)

    assert data['watch_url'] == 'https://sahid4u.com/watch/example-episode'
    assert data['download_url'] == 'https://sahid4u.com/download/example-episode'
    assert data['servers'][0]['url'] == 'https://fastvid.cam/embed/abc'
    assert data['qualities'] == ['720p']
    assert 'https://shhahhid4u.com/watch/example-episode' not in requested

    linked_html = '''
        <title>Example movie</title>
        <a href="https://shahidd4u.co/watch/canonical-slug">Watch</a>
        <a href="/download/canonical-slug">Download</a>
    '''
    with patch.object(sahid4u_api, '_fetch', return_value=linked_html):
        info = sahid4u_api.get_content_info('https://shahidd4u.co/film/old-slug')

    assert info['watch_url'] == 'https://shahidd4u.co/watch/canonical-slug'
    assert info['download_url'] == 'https://shahidd4u.co/download/canonical-slug'
    print('sahid4u api regressions: ok')


if __name__ == '__main__':
    run()
