import sys
sys.path.insert(0, './api')
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key='fc-186b4e776b4042dfa4043a97c4985cc9')

schema = {
    'type': 'object',
    'properties': {
        'qualities': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'quality': {'type': 'string'},
                    'url': {'type': 'string'}
                }
            }
        }
    }
}

try:
    res = app.extract(['https://hgcloud.to/e/wfr0okr6amrd'], {
        'prompt': 'Extract all video download source URLs directly to .mp4 or similar along with their quality strings (1080p, 720p). Look for source tags in the video player or download buttons.',
        'schema': schema
    })
    print(res)
except Exception as e:
    print(f"Error: {e}")
