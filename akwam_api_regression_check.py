import unittest
from unittest.mock import Mock, patch

from requests.exceptions import SSLError

from api.akwam_api import (
    AkwamAPI,
    _extract_media_url,
    _get_downet_media,
    _is_downet_url,
)


class AkwamMediaTests(unittest.TestCase):
    def test_quality_resolution_prefers_quality_specific_download_page(self):
        page = '''
        <a href="#tab-1">480p</a>
        <div class="tab-content quality" id="tab-1">
          <a href="https://akwam.it/watch/7055/562/inception-1" class="link-btn link-show">watch</a>
          <a href="https://akwam.it/download/7055/562/inception-1" class="link-btn link-download">
            <span class="font-size-14 mr-auto">727.2 MB</span>
          </a>
        </div></div>
        '''
        response = Mock(content=page.encode())
        api = object.__new__(AkwamAPI)

        with patch('api.akwam_api.safe_get', return_value=response):
            qualities = api.get_qualities('https://akwam.it/movie/562/inception-1')

        self.assertEqual(len(qualities), 1)
        self.assertEqual(qualities[0]['quality'], '480p')
        self.assertEqual(
            qualities[0]['link_id'],
            'https://akwam.it/download/7055/562/inception-1',
        )

    def test_extracts_relative_media_with_query_and_html_entities(self):
        page = '<source type="video/mp4" src="/media/video.mp4?x=1&amp;y=2">'
        self.assertEqual(
            _extract_media_url(page, 'https://akwam.it/watch/1'),
            'https://akwam.it/media/video.mp4?x=1&y=2',
        )

    def test_downet_host_check_rejects_lookalikes(self):
        self.assertTrue(_is_downet_url('https://s205d1.downet.net/video.mp4'))
        self.assertFalse(_is_downet_url('https://downet.net.example/video.mp4'))

    def test_tls_fallback_is_limited_to_downet(self):
        response = Mock()
        session = Mock()
        session.get.side_effect = [SSLError('bad chain'), response]

        actual = _get_downet_media(
            session,
            'https://s205d1.downet.net/video.mp4',
            headers={'Range': 'bytes=0-99'},
            stream=True,
        )

        self.assertIs(actual, response)
        self.assertEqual(session.get.call_count, 2)
        self.assertNotIn('verify', session.get.call_args_list[0].kwargs)
        self.assertFalse(session.get.call_args_list[1].kwargs['verify'])

        other_session = Mock()
        other_session.get.side_effect = SSLError('bad chain')
        with self.assertRaises(SSLError):
            _get_downet_media(other_session, 'https://example.com/video.mp4')
        self.assertEqual(other_session.get.call_count, 1)

    def test_stream_preserves_range_and_reports_mp4_type(self):
        response = Mock()
        response.status_code = 206
        response.headers = {
            'content-type': 'application/octet-stream',
            'content-length': '100',
            'content-range': 'bytes 0-99/1000',
            'accept-ranges': 'bytes',
        }
        session = Mock()
        session.get.return_value = response

        api = object.__new__(AkwamAPI)
        api.get_fresh_stream_url = Mock(return_value=(
            session,
            'https://s205d1.downet.net/video.mp4',
            'https://akwam.it/watch/1',
        ))

        actual, info = api.stream_video(
            'https://akwam.it/watch/1',
            'bytes=0-99',
        )

        self.assertIs(actual, response)
        self.assertEqual(info['status_code'], 206)
        self.assertEqual(info['content_type'], 'video/mp4')
        self.assertEqual(info['content_range'], 'bytes 0-99/1000')
        self.assertEqual(
            session.get.call_args.kwargs['headers']['Range'],
            'bytes=0-99',
        )


if __name__ == '__main__':
    unittest.main()
