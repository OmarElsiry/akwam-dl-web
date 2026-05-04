import sys
import json
sys.path.insert(0, '.')
from api.akwam_api import AkwamAPI

api = AkwamAPI()
results = api.search('batman')
output = {"results": results}

if results:
    url = results[0]['url']
    output['fetching'] = url
    qualities = api.get_qualities(url)
    output['qualities'] = qualities
    
    if qualities:
        link_id = qualities[0]['link_id']
        output['resolving'] = link_id
        direct = api.resolve_direct_url(link_id)
        output['direct'] = direct

with open('test_out2.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
