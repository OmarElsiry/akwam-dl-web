"""
Diagnostic script — Bloodhounds bulk link fetch
"""
import sys, os, re, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.akwam_api import AkwamAPI

api = AkwamAPI()
print(f"[BASE URL] {api.base_url}\n")

# ── 1. Search ─────────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Search for 'bloodhounds' (series)")
results = api.search("bloodhounds", type="series")
print(f"Found {len(results)} result(s):")
for r in results:
    print(f"  {r['name']}  =>  {r['url']}")

if not results:
    print("[FAIL] No search results. Stopping.")
    sys.exit(1)

series = results[0]
print(f"\n[SELECTED] {series['name']}")

# ── 2. Episodes ───────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"STEP 2 — Fetch episodes from: {series['url']}")
episodes = api.get_episodes(series['url'])
print(f"Found {len(episodes)} episode(s):")
for ep in episodes[:5]:
    print(f"  {ep['name']}  =>  {ep['url']}")
if len(episodes) > 5:
    print(f"  ... and {len(episodes)-5} more")

if not episodes:
    print("[FAIL] No episodes found. Stopping.")
    sys.exit(1)

# ── 3. Qualities for episode 1 ────────────────────────────────────────────
print("\n" + "=" * 60)
ep1 = episodes[0]
print(f"STEP 3 — Get qualities for episode 1: {ep1['url']}")
qualities = api.get_qualities(ep1['url'])
print(f"Found {len(qualities)} quality option(s):")
for q in qualities:
    print(f"  {q['quality']}  size={q.get('size','?')}  link_id={q['link_id']}")

if not qualities:
    print("[FAIL] No qualities found. Stopping.")
    sys.exit(1)

best = next((q for q in qualities if q['quality'] == '720p'), qualities[0])
print(f"\n[BEST QUALITY] {best['quality']}  link_id={best['link_id']}")

# ── 4. Resolve direct URL ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"STEP 4 — Resolve direct URL for link_id: {best['link_id']}")
direct = api.resolve_direct_url(best['link_id'])
print(f"[RESULT] {direct}")

if not direct:
    print("[FAIL] Could not resolve direct URL.")
else:
    print("[SUCCESS] Direct URL obtained!")

print("\n[DONE]")
