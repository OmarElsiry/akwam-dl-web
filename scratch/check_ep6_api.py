import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append('api')
from akwam_api import AkwamAPI

api = AkwamAPI()
ep6_url = 'https://akwam.com.co/episode/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6'
qualities = api.get_qualities(ep6_url)

print("Qualities:", qualities)

for q in qualities:
    link_id = q['link_id']
    url = api.resolve_direct_url(link_id)
    print(f"Quality {q['quality']} -> direct url: {url}")
