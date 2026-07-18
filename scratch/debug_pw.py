import traceback
from api.index import _playwright_get_video_url

link_id_url = "go.akwam.com.co/link/143994"
try:
    print("Testing Playwright resolution...")
    mp4_url, download_url, cookie_str = _playwright_get_video_url(link_id_url)
    print("Result:")
    print("mp4_url:", mp4_url)
    print("download_url:", download_url)
    print("cookie_str:", cookie_str)
except Exception as e:
    print("Exception!")
    traceback.print_exc()
