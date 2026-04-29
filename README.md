# 🛰️ Portfolio Wake System

A fully automated system to keep Streamlit Community Cloud apps alive, with a visual monitoring dashboard and GitHub Actions scheduling.

---

## Overview

Streamlit Community Cloud spins down free-tier apps after a period of inactivity, showing a **"Zzzz" sleep screen** to visitors. This project solves that by:

1. Using **Playwright** (a real browser automation tool) to visit each app, detect the sleep screen, and click the wake button
2. Running this automatically every **30 minutes** via **GitHub Actions**
3. Providing a **Streamlit monitoring dashboard** for manual runs with real-time log output and status cards

---

## Repository Structure

```
.
├── wake_apps.py              # Playwright script — visits each app and wakes it
├── monitor_dashboard.py      # Streamlit dashboard — manual control + live status
├── .github/
│   └── workflows/
│       └── wake.yml          # GitHub Actions workflow — scheduled cron trigger
└── README.md
```

---

## How It Works

### 1. `wake_apps.py`

The core script. Uses Playwright's async API to:

- Launch a headless Chromium browser
- Visit each Streamlit app URL
- Wait for the page HTML to load (`domcontentloaded` — fast, doesn't wait for data fetches)
- Check if the **"Yes, get this app back up!"** wake button is visible
- If found → click it and wait 30 seconds for the engine to boot
- If not found → app is already awake, move on
- Falls back to searching for "Zzzz" text if the button role differs

Key design decisions:
- Uses `domcontentloaded` instead of `networkidle` — the sleep screen is static HTML and loads instantly. `networkidle` would wait for all data fetches to complete (30–90 seconds per app) which is unnecessary
- Creates a **fresh page per URL** but reuses the same browser instance — clean session state without the overhead of relaunching Chromium each time
- All `print()` calls use `flush=True` — ensures log lines stream immediately to the subprocess pipe rather than buffering
- 30 second `asyncio.sleep()` after clicking — gives Streamlit's Python engine time to fully establish its WebSocket connection before moving on

### 2. `monitor_dashboard.py`

A Streamlit app that provides a visual interface for manual runs. Features:

- **Status cards** for each app — color coded: orange (pending), blue (checking), yellow (waking), green (awake), red (error)
- **Live log box** — white textbox with dark teal monospace font, updates in real time as `wake_apps.py` runs
- **Hover tooltip on error cards** — shows the actual error message from the log
- **5 minute timeout** — automatically resets the button if the script hangs
- **Last run timestamp** displayed in the header

The dashboard runs `wake_apps.py` as a subprocess using Python's `subprocess.Popen`, capturing stdout line by line into a `queue.Queue`. A background thread feeds the queue; the main Streamlit loop drains it every 2 seconds and updates session state.

### 3. `.github/workflows/wake.yml`

GitHub Actions workflow that:

- Triggers on a **cron schedule every 30 minutes** (`*/30 * * * *`)
- Also supports **manual trigger** via `workflow_dispatch` (the "Run workflow" button in the Actions tab)
- Spins up a **fresh Ubuntu VM** on every run
- Installs Python 3.12, Playwright, and Chromium with all system dependencies
- Runs `wake_apps.py` with the `-u` flag (unbuffered output) for clean log streaming
- VM is destroyed after the run completes

---

## Setup

### Prerequisites

- Python 3.12
- A GitHub repository (public or private)
- Streamlit apps deployed on Streamlit Community Cloud

### Local Installation

```bash
pip install playwright streamlit
playwright install --with-deps chromium
```

### Configuration

Edit the `APP_URLS` list at the top of both `wake_apps.py` and `monitor_dashboard.py`:

```python
APP_URLS = [
    "https://your-app.streamlit.app/",
    "https://your-other-app.streamlit.app/",
]
```

Also update `APP_LABELS` in `monitor_dashboard.py` with friendly display names:

```python
APP_LABELS = {
    "https://your-app.streamlit.app/": "My App Name",
}
```

### Running Locally

**Wake script only:**
```bash
python wake_apps.py
```

**Monitoring dashboard:**
```bash
streamlit run monitor_dashboard.py
```

**Debug mode (visible browser):**
Change `headless=True` to `headless=False` in `wake_apps.py` — you'll see the browser window open and interact with each app in real time.

### GitHub Actions Setup

1. Push the repository to GitHub
2. The `.github/workflows/wake.yml` file is automatically detected
3. Go to the **Actions** tab in your repo to see scheduled runs
4. Use **"Run workflow"** to trigger a manual run immediately
5. Click any run → click the job → expand **"Run Awakener"** to see full log output

> **Note:** GitHub may disable scheduled workflows on repos with no commits for 60+ days. If runs stop, make a small commit to re-enable them.

---

## GitHub Actions Workflow

```yaml
name: Wake Up Portfolio
on:
  schedule:
    - cron: '*/30 * * * *'   # every 30 minutes
  workflow_dispatch:           # manual trigger button

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Playwright
        run: |
          pip install playwright
          playwright install --with-deps chromium

      - name: Run Awakener
        run: python -u wake_apps.py
```

---

## Architecture

```
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
```

---

## Monitoring Dashboard

The dashboard (`monitor_dashboard.py`) is itself deployed as a Streamlit app and is included in `APP_URLS` — it wakes itself along with all the other apps.

**Status color guide:**

| Color | Meaning |
|-------|---------|
| 🟠 Orange | Pending — not yet checked |
| 🔵 Blue (pulsing) | Checking — browser visiting the URL |
| 🟡 Yellow (pulsing) | Waking — Zzz button found and clicked |
| 🟢 Green | Awake — no sleep screen detected |
| 🔴 Red | Error — hover for details |

---

## Design Decisions

**Why Playwright instead of simple HTTP pings?**

Simple HTTP requests (curl, requests.get) return a 200 OK from Streamlit's server even when the app is sleeping — the server is alive, but the app process is not. Playwright launches a real browser, loads the actual page HTML, and can detect and interact with the sleep screen UI element.

**Why `domcontentloaded` instead of `networkidle`?**

`networkidle` waits for all network activity to stop. On data-heavy apps (stock forecasting, ML models), this means waiting 30–90 seconds per app for API calls and model loads to complete. The sleep screen is purely static HTML and loads in 1–2 seconds — `domcontentloaded` fires as soon as the HTML is parsed, which is all we need to find and click the wake button.

**Why a fresh page per URL instead of reusing the same page?**

Reusing the same page object risks carrying session state, cookies, or a broken WebSocket from one app into the next. A fresh page ensures each app gets a clean browser session.

**Why 30 seconds sleep after clicking?**

After clicking the wake button, Streamlit starts its Python engine and establishes a WebSocket connection. If the script navigates away too quickly, Streamlit may not register a sustained enough connection and could go back to sleep. 30 seconds is enough for the engine to fully boot.

---

## Troubleshooting

**Apps still sleeping after runs**

Check the GitHub Actions log — look for `Error` lines. Common causes:
- App URL changed
- Streamlit changed the wake button text
- App is crashing on startup (check Streamlit Cloud logs separately)

**Workflow not triggering**

- Check the Actions tab — GitHub may have disabled the workflow due to repo inactivity
- Make a small commit to re-enable scheduled runs

**Dashboard log is empty**

- Make sure `flush=True` is on all `print()` calls in `wake_apps.py`
- Make sure `wake_apps.py` is in the same directory as `monitor_dashboard.py`

**One app takes much longer than others**

That app likely has a heavy startup — large dataset loads, ML model initialization, or slow external API calls. Consider adding `@st.cache_resource` or `@st.cache_data` to expensive operations in that app's code.

---

## Dependencies

```
playwright
streamlit
```

No other dependencies required. All standard library modules (`asyncio`, `subprocess`, `threading`, `queue`, `time`, `datetime`) are used for orchestration.

---

## Related Projects

This wake system is part of a broader portfolio infrastructure:

- **GitHub Pages** — main portfolio hub linking to all projects
- **Streamlit apps** — individual project demos (biomedtech, fintech, medical imaging, etc.)
- **This repo** — keeps all Streamlit apps alive automatically
