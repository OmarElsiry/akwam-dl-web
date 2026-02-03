import uvicorn
import threading
import webbrowser
import time
import os
import sys
from api.index import app

def start_server():
    # Use 0.0.0.0 to prevent some localhost binding issues on Windows
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

def main():
    print("---------------------------------------------------")
    print("      AKWAM PRO - STARTING DOWNLOADER...")
    print("---------------------------------------------------")
    print("[1/3] Initializing API Server...")
    
    # Start server in thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    print("[2/3] Waiting for server to respond...")
    time.sleep(2) # Give it a moment (simple wait)
    
    url = "http://127.0.0.1:8000"
    print(f"[3/3] Opening Interface at {url}")
    print(">> Close this window to stop the server.")
    
    # Open default browser
    webbrowser.open(url)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        sys.exit(0)

if __name__ == "__main__":
    main()
