GitHub Actions (cron: every 30 mins)
        │
        ▼
  ubuntu-latest VM
        │
        ├── pip install playwright
        ├── playwright install --with-deps chromium
        │
        ▼
   wake_apps.py
        │
        ├── For each URL:
        │     ├── page.goto(url, wait_until="domcontentloaded")
        │     ├── Check for wake button
        │     ├── Click if found → asyncio.sleep(30)
        │     └── Log result
        │
        ▼
  Streamlit Cloud
  (apps stay alive)