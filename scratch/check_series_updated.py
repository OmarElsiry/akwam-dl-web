import sys
sys.path.append('api')
from akwam_api import AkwamAPI
import json

sys.stdout.reconfigure(encoding='utf-8')

api = AkwamAPI()
eps = api.get_episodes('https://akwam.com.co/series/4277/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84')
print(f"Total episodes: {len(eps)}")
for ep in eps:
    print(ep['name'], "->", ep['url'])
    
    # get qualities for this ep
    qualities = api.get_qualities(ep['url'])
    for q in qualities:
        print(f"  Quality {q['quality']}: link_id = {q['link_id']}")
        
