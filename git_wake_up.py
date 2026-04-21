import requests
import time
from site_urls import projects
 
APP_URLS = [p['url'] for p in projects]
def wake_up():
    for url in APP_URLS:
        try:
            # We just "poke" the URL. 
            # timeout=30 ensures we wait long enough for the 'spin up' to start
            response = requests.get(url, timeout=30)
            print(f"Pinged {url} - Status Code: {response.status_code}")
        except Exception as e:
            print(f"Failed to reach {url}: {e}")

if __name__ == "__main__":
    wake_up()
