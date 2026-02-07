from api.akwam_api import AkwamAPI
import json

def test():
    api = AkwamAPI()
    
    print("Testing Search...")
    results = api.search("Matrix", "movie")
    print(f"Found {len(results)} movies.")
    if results:
        target = results[0]
        print(f"Selecting: {target['name']}")
        
        print("Fetching Qualities...")
        qualities = api.get_qualities(target['url'])
        print(f"Available qualities: {[q['quality'] for q in qualities]}")
        
        if qualities:
            print("Resolving Direct URL...")
            direct = api.resolve_direct_url(qualities[0]['link_id'])
            print(f"Final URL: {direct}")

if __name__ == "__main__":
    test()
