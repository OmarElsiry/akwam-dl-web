import requests
import json
import urllib.parse
import sys

BASE_URL = "https://akwam-dl-web-ul8s.vercel.app/api/akwam"

def test_movie():
    print("--- TESTING MOVIE: Inception ---")
    try:
        # 1. Search
        search_res = requests.get(f"{BASE_URL}?action=search&q=inception&type=movie").json()
        if not search_res or not isinstance(search_res, list) or len(search_res) == 0:
            print(f"FAIL: No results found for Inception (Response: {search_res})")
            return
        
        movie = search_res[0]
        print(f"Found: {movie['title']} ({movie['url']})")
        
        # 2. Details (Qualities)
        details_res = requests.get(f"{BASE_URL}?action=details&url={urllib.parse.quote(movie['url'])}").json()
        if not details_res or not isinstance(details_res, dict):
            print(f"FAIL: No qualities found for {movie['title']} (Response: {details_res})")
            return
        
        if len(details_res) == 0:
            print("FAIL: Quality dictionary is empty")
            return

        quality = list(details_res.keys())[0]
        quality_url = details_res[quality]
        print(f"First Quality Available: {quality} -> {quality_url}")
        
        # 3. Resolve
        resolve_res = requests.get(f"{BASE_URL}?action=resolve&url={urllib.parse.quote(quality_url)}").json()
        if 'direct_url' in resolve_res and resolve_res['direct_url']:
            print(f"SUCCESS: Direct Link: {resolve_res['direct_url']}")
        else:
            print(f"FAIL: Resolution failed. Response: {resolve_res}")
    except Exception as e:
        print(f"CRITICAL ERROR in test_movie: {str(e)}")

def test_series():
    print("\n--- TESTING SERIES: Dark ---")
    try:
        # 1. Search
        search_res = requests.get(f"{BASE_URL}?action=search&q=dark&type=series").json()
        if not search_res or not isinstance(search_res, list) or len(search_res) == 0:
            print(f"FAIL: No results found for Dark (Response: {search_res})")
            return
        
        series = search_res[0]
        print(f"Found: {series['title']} ({series['url']})")
        
        # 2. Episodes list
        episodes_res = requests.get(f"{BASE_URL}?action=episodes&url={urllib.parse.quote(series['url'])}").json()
        if not episodes_res or not isinstance(episodes_res, list) or len(episodes_res) == 0:
            print(f"FAIL: No episodes found for {series['title']} (Response: {episodes_res})")
            return
        
        episode = episodes_res[0]
        print(f"First Episode Selected: {episode['title']} ({episode['url']})")
        
        # 3. Episode Qualities
        ep_details_res = requests.get(f"{BASE_URL}?action=details&url={urllib.parse.quote(episode['url'])}").json()
        if not ep_details_res or not isinstance(ep_details_res, dict) or len(ep_details_res) == 0:
            print(f"FAIL: No qualities for episode found (Response: {ep_details_res})")
            return
        
        quality = list(ep_details_res.keys())[0]
        quality_url = ep_details_res[quality]
        print(f"Quality Selected: {quality} -> {quality_url}")
        
        # 4. Resolve
        resolve_res = requests.get(f"{BASE_URL}?action=resolve&url={urllib.parse.quote(quality_url)}").json()
        if 'direct_url' in resolve_res and resolve_res['direct_url']:
            print(f"SUCCESS: Direct Link: {resolve_res['direct_url']}")
        else:
            print(f"FAIL: Resolution failed. Response: {resolve_res}")
    except Exception as e:
        print(f"CRITICAL ERROR in test_series: {str(e)}")

if __name__ == "__main__":
    test_movie()
    test_series()
