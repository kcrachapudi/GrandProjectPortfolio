# =============================================================================
# monitor_dashboard.py
# =============================================================================
# PURPOSE:
#   A Streamlit web app that serves as a visual control panel for the portfolio
#   wake system. It lets you manually trigger wake_apps.py, watch its output
#   in real time, and see each Streamlit app's current status as a color-coded
#   card.
#
# HOW IT WORKS (high level):
#   1. User clicks "Check / Wake All" button
#   2. wake_apps.py is launched as a background subprocess (separate process)
#   3. A background thread reads the subprocess output line by line into a Queue
#   4. Every 2 seconds, Streamlit reruns itself, drains the Queue, and updates
#      the status cards and log box in real time
#   5. When the subprocess finishes, it sends a "__DONE__" sentinel signal and
#      the auto-refresh stops
#
# NOTE:
#   This dashboard is for MANUAL use only. Automated waking is handled by
#   GitHub Actions running wake_apps.py on a cron schedule (every 30 mins).
#   You do not need this dashboard running for the automation to work.
#
# REQUIRES:
#   pip install streamlit playwright
#   playwright install --with-deps chromium
#   wake_apps.py must be in the same directory as this file
# =============================================================================

import streamlit as st   # The web app framework - handles UI, state, reruns
import subprocess        # Used to launch wake_apps.py as a child process
import threading         # Used to read subprocess output without blocking the UI
import time              # Used for sleep (auto-refresh delay) and timeout tracking
import queue             # Thread-safe queue: background thread writes, main loop reads
from datetime import datetime  # Used to format the "last run" timestamp

# =============================================================================
# PAGE CONFIG
# =============================================================================
# Must be the FIRST Streamlit call in the script.
# layout="wide" uses the full browser width instead of Streamlit's default
# narrow centered column.
# =============================================================================
st.set_page_config(page_title="Portfolio Monitor", page_icon="🛰️", layout="wide")


# =============================================================================
# APP URLS
# =============================================================================
# The list of Streamlit apps to check and wake.
# These are passed to wake_apps.py indirectly — wake_apps.py has its own
# identical list. This list is used HERE only for:
#   - Displaying the status cards in the correct order
#   - Matching log output lines back to specific URLs (in parse_status)
#
# IMPORTANT: Keep this list in sync with the APP_URLS list in wake_apps.py.
# If you add or remove an app from wake_apps.py, do the same here.
# =============================================================================
APP_URLS = [
    "https://bioinform1.streamlit.app/",
    "https://bioinform2.streamlit.app/",
    "https://medistream-ai-ready-medical-imaging-pipeline.streamlit.app/",
    "https://smartcreditriskloaneligibilityengine.streamlit.app/",
    "https://stockmarketperformanceandforecastingengine.streamlit.app/",
    "https://real-timetransactionfrauddetectionsystem.streamlit.app/",
    "https://rad-kalyan-rachapudi-recruiter.streamlit.app/",
]


# =============================================================================
# APP LABELS
# =============================================================================
# Human-friendly display names for each URL, shown as the card title.
# This is a dict so we can look up the label by URL key: APP_LABELS[url]
# If a URL is not in this dict, the raw URL is used as a fallback (see cards
# section below: APP_LABELS.get(url, url))
# =============================================================================
APP_LABELS = {
    "https://bioinform1.streamlit.app/": "BioInform 1",
    "https://bioinform2.streamlit.app/": "BioInform 2",
    "https://medistream-ai-ready-medical-imaging-pipeline.streamlit.app/": "MediStream AI",
    "https://smartcreditriskloaneligibilityengine.streamlit.app/": "Smart Credit Risk",
    "https://stockmarketperformanceandforecastingengine.streamlit.app/": "Stock Forecast",
    "https://real-timetransactionfrauddetectionsystem.streamlit.app/": "Fraud Detection",
    "https://rad-kalyan-rachapudi-recruiter.streamlit.app/": "Recruiter Portfolio",
}


# =============================================================================
# STATUS CONFIG
# =============================================================================
# Maps each status string to its visual styling (colors, label text).
# Each status has:
#   bg     - card background color (dark themed)
#   border - card border color (matches the status theme)
#   dot    - the small circular indicator dot color
#   text   - the status label text color
#   label  - the ALL CAPS text shown on the card (e.g. "AWAKE", "PENDING")
#
# These status strings must exactly match what parse_status() returns.
# The dot pulses (animates) for CHECKING and WAKING states — see CSS .pulse class.
#
# COLOR GUIDE:
#   PENDING    -> orange  (not yet touched)
#   CHECKING   -> blue    (browser is visiting the URL right now)
#   ZZZ WAKING -> yellow  (Zzz button was found and clicked, waiting for boot)
#   AWAKE      -> green   (no sleep screen detected — app was already running)
#   WOKEN      -> green   (was asleep, successfully woken this run)
#   ERROR      -> red     (something went wrong — hover the card to see details)
# =============================================================================
STATUS_CONFIG = {
    "⏳ Pending":      {"bg": "#1e1e2e", "border": "#cc5500", "dot": "#ff6a00", "text": "#ff6a00", "label": "PENDING"},
    "🔍 Checking...":  {"bg": "#1a2535", "border": "#2a4a7a", "dot": "#4a8fd4", "text": "#7ab3e8", "label": "CHECKING"},
    "🔔 Waking...":    {"bg": "#2a1f00", "border": "#ccaa00", "dot": "#ffe600", "text": "#ffe600", "label": "ZZZ WAKING"},
    "✅ Awake":        {"bg": "#002a10", "border": "#00cc55", "dot": "#00ff66", "text": "#00ff66", "label": "AWAKE"},
    "✅ Woken":        {"bg": "#002a10", "border": "#00cc55", "dot": "#00ff66", "text": "#00ff66", "label": "WOKEN"},
    "❌ Error":        {"bg": "#2a0a0a", "border": "#7a2020", "dot": "#e24b4a", "text": "#f07070", "label": "ERROR"},
}


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
# Streamlit reruns the ENTIRE script from top to bottom on every interaction
# (button click, slider move, auto-refresh, etc.). Session state is the only
# way to persist data across those reruns — it survives as long as the browser
# tab is open.
#
# The "if X not in st.session_state" pattern is the standard Streamlit idiom
# for initializing a value ONLY on the very first run. Without this check,
# we'd reset everything on every rerun, losing all our data.
#
# VARIABLES:
#   statuses       - dict mapping each URL to its current status string
#                    e.g. {"https://...app1": "✅ Awake", "https://...app2": "⏳ Pending"}
#   running        - bool flag: True while wake_apps.py subprocess is active
#   log_queue      - thread-safe Queue object shared between the background thread
#                    and the main Streamlit loop for passing log lines
#   logs           - list of all log lines received so far in this run
#                    (persisted in session state so they survive reruns)
#   last_run       - formatted timestamp string of the last completed run
#                    e.g. "Apr 29 2026  14:32:01"
#   error_messages - dict mapping URLs that errored to their error log line
#                    used to show the error detail on hover over the card
#   start_time     - float unix timestamp of when the current run started
#                    used for the 5-minute timeout check
# =============================================================================
if "statuses" not in st.session_state:
    # Initialize all apps to Pending at startup
    st.session_state.statuses = {url: "⏳ Pending" for url in APP_URLS}

if "running" not in st.session_state:
    st.session_state.running = False

if "log_queue" not in st.session_state:
    # queue.Queue is thread-safe: the background thread can put() into it
    # while the main Streamlit loop get_nowait()s from it without conflict
    st.session_state.log_queue = queue.Queue()

if "logs" not in st.session_state:
    st.session_state.logs = []

if "last_run" not in st.session_state:
    st.session_state.last_run = None

if "error_messages" not in st.session_state:
    st.session_state.error_messages = {}

if "start_time" not in st.session_state:
    st.session_state.start_time = None


# =============================================================================
# FUNCTION: parse_status
# =============================================================================
# PURPOSE:
#   Reads a single log line printed by wake_apps.py and figures out which
#   URL it refers to and what status to assign to that URL's card.
#
# HOW IT WORKS:
#   - Loops through every URL in APP_URLS
#   - Checks if that URL appears anywhere in the log line (the print statements
#     in wake_apps.py always include the URL being processed)
#   - Keyword-matches the line text to decide the new status
#   - Returns a COPY of the statuses dict with the matched URL updated
#     (we return a copy rather than mutating in place to be safe)
#
# PARAMETERS:
#   line     - a single string line from wake_apps.py stdout
#   statuses - the current statuses dict from session state
#
# RETURNS:
#   updated dict with potentially one URL's status changed
#
# KEYWORD MAPPING (matches wake_apps.py print statements):
#   "genuinely awake"         -> ✅ Awake    (no Zzz screen found)
#   "detected zzz" / "clicking wake" -> 🔔 Waking... (Zzz button found, clicking)
#   "wake signal sent"        -> ✅ Woken    (button clicked, wait complete)
#   "error"                   -> ❌ Error    (exception caught in wake_apps.py)
#   "checking"                -> 🔍 Checking... (browser navigating to URL)
# =============================================================================
def parse_status(line, statuses):
    updated = dict(statuses)  # Make a copy so we don't mutate the original
    for url in APP_URLS:
        # Check if this log line is about this particular URL
        # We check both with and without trailing slash for safety
        if url in line or url.rstrip("/") in line:
            ll = line.lower()  # Lowercase once for all comparisons
            if "genuinely awake" in ll:
                updated[url] = "✅ Awake"
            elif "detected zzz" in ll or "clicking wake" in ll:
                updated[url] = "🔔 Waking..."
            elif "wake signal sent" in ll:
                updated[url] = "✅ Woken"
            elif "error" in ll:
                updated[url] = "❌ Error"
                # Also save the full error line so we can show it on hover
                st.session_state.error_messages[url] = line
            elif "checking" in ll:
                updated[url] = "🔍 Checking..."
    return updated


# =============================================================================
# FUNCTION: run_wake_script
# =============================================================================
# PURPOSE:
#   Launches wake_apps.py as a child process and streams its stdout output
#   into the shared Queue line by line. Runs in a background thread so the
#   Streamlit UI stays responsive while the script runs.
#
# WHY A BACKGROUND THREAD?
#   Streamlit's main thread handles the UI. If we ran the subprocess
#   synchronously (blocking), the entire UI would freeze until wake_apps.py
#   finished — which could take several minutes. By running it in a daemon
#   thread, the subprocess runs in parallel and the main thread continues
#   doing reruns and UI updates every 2 seconds.
#
# WHY daemon=True?
#   Daemon threads are automatically killed when the main program exits.
#   Without daemon=True, Python would wait for this thread to finish before
#   exiting, which could cause the Streamlit server to hang on shutdown.
#
# KEY subprocess.Popen FLAGS:
#   -u flag       : Runs Python in unbuffered mode — print() output goes
#                   directly to the pipe immediately instead of being held
#                   in Python's internal output buffer. Without this, we'd
#                   see no output until the buffer fills up (usually 8KB).
#   stdout=PIPE   : Captures the child process's stdout so we can read it
#   stderr=STDOUT : Merges stderr into stdout so error messages also appear
#                   in our log box (otherwise errors would be invisible)
#   text=True     : Returns strings instead of bytes (no need to decode)
#   bufsize=1     : Line-buffered reading — we get one line at a time
#
# THE SENTINEL "__DONE__":
#   After the subprocess exits, we put a special "__DONE__" string into
#   the queue. The main loop checks for this to know the run is complete
#   and should stop the auto-refresh and reset the running flag.
#
# PARAMETERS:
#   log_q - the queue.Queue from session state to write lines into
# =============================================================================
def run_wake_script(log_q):
    proc = subprocess.Popen(
        ["python", "-u", "wake_apps.py"],  # -u = unbuffered stdout
        stdout=subprocess.PIPE,             # capture stdout
        stderr=subprocess.STDOUT,           # merge stderr into stdout
        text=True,                          # return strings not bytes
        bufsize=1,                          # line buffered
    )
    # Read stdout line by line as it arrives (this loop blocks in the thread
    # until each new line appears — that's fine since we're in a background thread)
    for line in proc.stdout:
        stripped = line.rstrip()   # Remove trailing newline/whitespace
        if stripped:               # Skip empty lines
            log_q.put(stripped)    # Push line into the queue for the main loop

    proc.wait()            # Wait for the subprocess to fully exit
    log_q.put("__DONE__")  # Signal to the main loop that we're finished


# =============================================================================
# CSS STYLES
# =============================================================================
# All custom styling is injected via st.markdown with unsafe_allow_html=True.
# Streamlit renders this inside an iframe, so we use !important on some rules
# to override Streamlit's own default styles.
#
# WHY NOT USE STREAMLIT'S BUILT-IN COMPONENTS?
#   Streamlit's native components (st.text_area, st.metric, etc.) have their
#   own opinionated styling that's very hard to override. Using raw HTML divs
#   with our own CSS gives us 100% control over the look.
#
# FONTS:
#   Outfit       - modern geometric sans-serif for headings and card titles
#   IBM Plex Mono - monospace for URLs, status labels, log output (technical feel)
#   Both loaded from Google Fonts via @import
#
# SIDEBAR HIDING:
#   Streamlit auto-generates a sidebar with page navigation if it detects
#   multiple pages (files in a /pages folder). We hide it completely since
#   this is a single-page utility app.
#   Multiple selectors are used because Streamlit's internal CSS class names
#   change between versions, so we target the stable data-testid attributes.
#
# CARD DESIGN:
#   Each app card uses CSS custom property --accent (set inline per card)
#   for the top gradient line. This lets each card have its own accent color
#   without needing separate CSS classes for each status.
#
# PULSING DOT:
#   The .pulse animation (blink keyframe) runs on the status dot for
#   CHECKING and WAKING states to give a visual "in progress" indicator.
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Outfit:wght@400;600;800&display=swap');

/* Apply border-box sizing globally so padding doesn't expand element widths */
*, *::before, *::after { box-sizing: border-box; }

/* ── Hide Streamlit's auto-generated sidebar and collapse toggle ── */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebarContent"] { display: none !important; }
.st-emotion-cache-1cypcdb { display: none !important; }  /* fallback class */

/* ── Header bar: title on left, last-run timestamp on right ── */
.mon-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #003a30;  /* subtle teal-tinted separator */
}
/* Main title — Cambria serif, large, turquoise */
.mon-title {
    font-family: Cambria, Georgia, serif;
    font-weight: bold;
    font-size: 2.8rem;
    letter-spacing: -1px;
    color: #00e5cc;    /* turquoise base color */
    margin: 0;
    line-height: 1;
}
/* "Monitor" word gets a gradient via background-clip trick */
.mon-title span {
    background: linear-gradient(90deg, #00e5cc, #00aaff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
/* Small uppercase subtitle below the title */
.mon-subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #007a6a;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 6px;
}
/* Last run timestamp (top right of header) */
.mon-lastrun {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #007a6a;
    text-align: right;
    line-height: 1.6;
}

/* ── App cards grid layout ── */
/* auto-fill: creates as many columns as fit in the width
   minmax(280px, 1fr): each column is at least 280px, grows equally */
.app-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    margin-bottom: 1.5rem;
}

/* Individual app card */
.app-card {
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid;       /* color set inline per card via style attribute */
    position: relative;      /* needed for the ::before pseudo-element */
    overflow: hidden;        /* clips the ::before gradient at rounded corners */
    transition: transform 0.15s ease;
}
/* Subtle lift on hover */
.app-card:hover { transform: translateY(-2px); }
/* Top accent line — uses --accent CSS variable set per card inline */
.app-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0.7;
}

/* App name (friendly label, e.g. "MediStream AI") */
.card-label {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    color: #e0e0ff;
    margin-bottom: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;  /* shows "..." if label is too long for card width */
}
/* Full URL shown in smaller muted text below the label */
.card-url {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    color: #7a7aaa;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 14px;
}
/* Bottom row of card: dot + status label + optional error hint */
.card-footer {
    display: flex;
    align-items: center;
    gap: 8px;
}
/* Small colored circle indicator */
.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;  /* prevents dot from shrinking if footer is narrow */
}
/* Pulsing animation for active states (CHECKING, WAKING) */
.status-dot.pulse {
    animation: blink 1.3s ease-in-out infinite;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.25; }  /* fades to 25% then back */
}
/* Status text label (e.g. "AWAKE", "PENDING") */
.status-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 2px;  /* spaced-out caps look for technical feel */
}

/* ── Log box ── */
/* "LOG" label above the box */
.log-label {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.65rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #00e5cc;
    margin-bottom: 6px;
}
/* The white scrollable log container */
.log-box {
    background: #ffffff;
    border: 1px solid #00ccaa;
    border-radius: 10px;
    padding: 12px 16px;
    height: 120px;       /* fixed height — similar to a chat input box */
    overflow-y: auto;    /* scrollable when content exceeds height */
    margin-bottom: 1rem;
}
/* Each individual log line — !important needed to beat Streamlit's CSS */
.log-row {
    font-family: "IBM Plex Mono", monospace !important;
    font-size: 0.95rem !important;
    font-weight: bold !important;
    color: #005544 !important;  /* dark teal for readability on white */
    line-height: 1.9 !important;
}
/* Placeholder text shown when no logs exist yet */
.log-placeholder {
    color: #aacccc;
    font-style: italic;
}

/* ── Error hint shown on cards with errors ── */
/* Small italic text "hover for details" next to the ERROR label */
.error-hint {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.58rem;
    color: #e24b4a;
    opacity: 0.7;
    margin-left: 6px;
    font-style: italic;
}

/* ── Section title (e.g. "APPS") above the cards grid ── */
.section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #007a6a;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

/* ── Legacy log styles (unused but kept for reference) ── */
.log-wrap {
    background: #0a0f2e;
    border: 1px solid #1a2560;
    border-radius: 10px;
    padding: 14px 18px;
    height: 120px;
    overflow-y: auto;
}
.log-line { font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: #333355; line-height: 1.9; }
.log-line.awake  { color: #1de9a0; }
.log-line.waking { color: #f5c060; }
.log-line.error  { color: #e24b4a; }
.log-line.check  { color: #4a8fd4; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# HEADER
# =============================================================================
# Renders the top bar with:
#   - "Portfolio Monitor" title (left)
#   - Last run timestamp (right, or "Never run" if no run has happened yet)
#
# We build the last_run HTML snippet conditionally first, then inject it into
# the main header template string. This keeps the f-string clean and avoids
# nested conditional expressions inside HTML.
# =============================================================================
last_run_html = (
    f'<div class="mon-lastrun">Last run<br>{st.session_state.last_run}</div>'
    if st.session_state.last_run
    else '<div class="mon-lastrun">Never run</div>'
)
st.markdown(f"""
<div class="mon-header">
  <div>
    <div class="mon-title">Portfolio <span>Monitor</span></div>
    <div class="mon-subtitle">Streamlit App Status Dashboard</div>
  </div>
  {last_run_html}
</div>
""", unsafe_allow_html=True)


# =============================================================================
# MAIN BUTTON — "Check / Wake All"
# =============================================================================
# The button label changes based on running state:
#   - "🚀 Check / Wake All" when idle (click to start)
#   - "⏳ Running..."       when active (disabled, can't click again)
#
# disabled=st.session_state.running prevents double-clicking while a run is
# already in progress.
#
# WHAT HAPPENS ON CLICK:
#   1. Reset all app statuses back to "⏳ Pending"
#   2. Clear the previous run's logs
#   3. Create a fresh Queue (discarding any leftover items from last run)
#   4. Set running=True (changes button label, enables auto-refresh)
#   5. Record start_time for the 5-minute timeout check
#   6. Clear previous error messages
#   7. Immediately append a "started" line to logs so the box isn't empty
#   8. Start the background thread that runs wake_apps.py
#
# NOTE: We do NOT call st.rerun() here. Streamlit automatically reruns
# after a button click. If we called st.rerun() explicitly, it would fire
# before the thread had time to write any lines to the queue, causing a
# race condition where the log box stays empty on the first rerun.
# =============================================================================
btn_label = "⏳  Running..." if st.session_state.running else "🚀  Check / Wake All"
if st.button(btn_label, disabled=st.session_state.running):
    # Reset everything for a clean new run
    st.session_state.statuses = {url: "⏳ Pending" for url in APP_URLS}
    st.session_state.logs = []
    st.session_state.log_queue = queue.Queue()   # Fresh queue — old one discarded
    st.session_state.running = True
    st.session_state.start_time = time.time()    # Record start for timeout
    st.session_state.error_messages = {}         # Clear previous errors

    # Write an immediate startup message directly to logs (not via queue)
    # so the log box shows something right away before the subprocess starts
    st.session_state.logs.append(
        f"🚀 Wake sequence started at {datetime.now().strftime('%H:%M:%S')} "
        f"— checking {len(APP_URLS)} apps..."
    )

    # Launch wake_apps.py in a background thread
    # daemon=True means this thread dies automatically if Streamlit shuts down
    threading.Thread(
        target=run_wake_script,
        args=(st.session_state.log_queue,),  # Pass the queue so thread can write to it
        daemon=True,
    ).start()


# =============================================================================
# TIMEOUT CHECK (5 MINUTES)
# =============================================================================
# Safety net: if wake_apps.py takes more than 5 minutes, we force-stop
# the running state so the button resets and the UI doesn't get stuck.
#
# This handles edge cases like:
#   - wake_apps.py hanging indefinitely on a URL
#   - The subprocess crashing without sending "__DONE__"
#   - Network timeouts that exceed Playwright's own timeout
#
# 300 seconds = 5 minutes.
# time.time() returns a float unix timestamp (seconds since epoch).
# Subtracting start_time gives elapsed seconds.
# =============================================================================
if st.session_state.running and st.session_state.start_time:
    elapsed = time.time() - st.session_state.start_time
    if elapsed > 300:
        st.session_state.running = False
        st.session_state.logs.append("⚠️ Timed out after 5 minutes.")


# =============================================================================
# QUEUE DRAIN — Pull new log lines into session state
# =============================================================================
# This runs on EVERY Streamlit rerun (every 2 seconds while running, and
# also on button clicks and other interactions).
#
# We drain the queue regardless of whether running=True because lines can
# still be in the queue even after the subprocess sends "__DONE__" — there
# might be a brief window where running flips to False but lines haven't
# been processed yet.
#
# get_nowait() is non-blocking: it returns immediately with either a line
# or raises queue.Empty. We catch all exceptions (bare except) as a safety
# net in case of any unexpected queue state.
#
# THE "__DONE__" SENTINEL:
#   When run_wake_script finishes reading all subprocess output, it puts
#   "__DONE__" into the queue. We check for this here to:
#     - Set running=False (stops auto-refresh on next cycle)
#     - Record the completion timestamp for the header
# =============================================================================
q = st.session_state.log_queue
while not q.empty():
    try:
        line = q.get_nowait()  # Non-blocking — raises Empty if queue is empty
        if line == "__DONE__":
            # Subprocess finished — stop the auto-refresh and record time
            st.session_state.running = False
            st.session_state.last_run = datetime.now().strftime("%b %d %Y  %H:%M:%S")
        else:
            # Regular log line — append to logs list and update status cards
            st.session_state.logs.append(line)
            st.session_state.statuses = parse_status(line, st.session_state.statuses)
    except:
        break  # queue.Empty or any other issue — just stop draining


# =============================================================================
# LOG BOX
# =============================================================================
# Renders a white scrollable box showing the last 60 lines of log output.
#
# WHY NOT st.text_area?
#   st.text_area with disabled=True grays out the text via -webkit-text-fill-color
#   which ignores our color CSS even with !important. Using a raw HTML div
#   gives us complete control over all styling.
#
# HOW IT WORKS:
#   - Takes the last 60 lines from session_state.logs (slicing with [-60:])
#   - Wraps each line in a <div class="log-row"> for styling
#   - If no logs exist, shows a placeholder message
#   - The > prefix on each line is a visual convention (like a terminal prompt)
#
# NOTE: The log box does NOT auto-scroll to the bottom on each rerun. Since
# the div is re-rendered fresh each time, the browser resets scroll to the
# top. Newer lines appear at the bottom — users can manually scroll down,
# or watch from the bottom. This is acceptable for our use case.
# =============================================================================
log_lines = st.session_state.logs[-60:] if st.session_state.logs else []
log_rows = (
    "".join(f'<div class="log-row">&gt; {line}</div>' for line in log_lines)
    or '<div class="log-row log-placeholder">Log output will appear here...</div>'
)
st.markdown(f"""
<div class="log-label">LOG</div>
<div class="log-box">{log_rows}</div>
""", unsafe_allow_html=True)

# Small vertical spacer between log box and cards grid
st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# =============================================================================
# APP STATUS CARDS GRID
# =============================================================================
# Renders one card per app showing its current status.
#
# WHY BUILD HTML MANUALLY INSTEAD OF USING st.columns?
#   Streamlit's column layout is fixed-width and doesn't support CSS Grid's
#   auto-fill behavior. Our CSS Grid auto-fills as many columns as fit in the
#   current browser width, making it naturally responsive.
#
# CARD STRUCTURE (per app):
#   - Dark background colored by status (from STATUS_CONFIG)
#   - 2px gradient line at top (via ::before CSS pseudo-element + --accent var)
#   - App label (friendly name, e.g. "MediStream AI")
#   - App URL (full URL, truncated with ellipsis if too long)
#   - Footer row: colored dot + status label text + optional error hint
#
# TOOLTIP ON ERROR CARDS:
#   We use the native HTML title attribute on the card div for hover tooltips.
#   This shows the raw error message from wake_apps.py when you hover over
#   a red error card. Quotes in the error message are replaced with single
#   quotes to avoid breaking the HTML attribute syntax.
#
# PULSING DOT:
#   The "pulse" CSS class is added to the dot for CHECKING and WAKING states
#   to give a visual "in progress" indicator. The blink keyframe animation
#   is defined in the CSS above.
#
# NOTE ON VARIABLE EXTRACTION:
#   We pull cfg dict values into plain variables (bg, border, etc.) before
#   building the HTML string. This avoids f-string-inside-f-string nested
#   quote issues that would break the HTML rendering.
# =============================================================================
st.markdown('<div class="section-title">Apps</div>', unsafe_allow_html=True)

cards_html = '<div class="app-grid">'

for url in APP_URLS:
    # Look up this URL's current status from session state
    status = st.session_state.statuses[url]

    # Get the visual config for this status (colors, label text)
    # Fall back to PENDING config if somehow we get an unknown status string
    cfg = STATUS_CONFIG.get(status, STATUS_CONFIG["⏳ Pending"])

    # Get friendly label — fall back to the raw URL if not in APP_LABELS
    label = APP_LABELS.get(url, url)

    # Pulsing dot for active states only
    pulse = "pulse" if status in ("🔍 Checking...", "🔔 Waking...") else ""

    # Error tooltip — only present if this URL had an error this run
    error_msg = st.session_state.error_messages.get(url, "")
    tooltip_attr = 'title="' + error_msg.replace('"', "'") + '"' if error_msg else ""

    # "hover for details" hint text — only shown on error cards
    hint_span = '<span class="error-hint">hover for details</span>' if error_msg else ""

    # Extract dict values to plain variables — avoids nested f-string quote chaos
    bg           = cfg['bg']      # card background color
    border       = cfg['border']  # card border color
    accent       = cfg['dot']     # top gradient accent color (CSS --accent var)
    dot_color    = cfg['dot']     # status indicator dot color
    status_label = cfg['label']   # status text e.g. "AWAKE"
    status_text  = cfg['text']    # status text color

    # Build the card HTML using string concatenation (safer than nested f-strings)
    cards_html += (
        f'<div class="app-card" style="background:{bg}; border-color:{border}; --accent:{accent};" {tooltip_attr}>'
        f'<div class="card-label">{label}</div>'           # Friendly name
        f'<div class="card-url">{url}</div>'               # Full URL
        f'<div class="card-footer">'
        f'<div class="status-dot {pulse}" style="background:{dot_color};"></div>'  # Colored dot
        f'<span class="status-label" style="color:{status_text};">{status_label}</span>'  # Status text
        f'{hint_span}'                                      # "hover for details" (errors only)
        f'</div></div>'
    )

cards_html += '</div>'  # Close the grid div
st.markdown(cards_html, unsafe_allow_html=True)


# =============================================================================
# AUTO-REFRESH LOOP
# =============================================================================
# While wake_apps.py is running, we need Streamlit to keep re-running itself
# so it can drain the queue and update the UI.
#
# HOW IT WORKS:
#   - If running=True, we sleep for 2 seconds then call st.rerun()
#   - st.rerun() restarts the script from the top (like a page refresh)
#   - On each rerun, the queue drain section above picks up new log lines
#   - The cards update, the log box updates, and then we sleep 2s again
#   - This continues until running=False (set by "__DONE__" or timeout)
#
# WHY 2 SECONDS?
#   1 second felt too fast (unnecessary reruns for apps that take 30s each).
#   2 seconds gives a good balance between responsiveness and efficiency.
#   The UI still feels "live" while not hammering Streamlit with reruns.
#
# WHY time.sleep() BEFORE st.rerun()?
#   The sleep happens AFTER the page has fully rendered (cards, log box, etc.)
#   so the user sees the updated UI for 2 seconds before the next rerun.
#   Without the sleep, reruns would stack up so fast the UI would flicker.
#
# WHEN DOES THIS STOP?
#   When running=False (set in the queue drain when "__DONE__" arrives, or
#   by the 5-minute timeout check). The if condition fails, sleep/rerun
#   are skipped, and Streamlit goes idle until the next user interaction.
# =============================================================================
if st.session_state.running:
    time.sleep(2)   # Wait 2 seconds (UI is visible to user during this time)
    st.rerun()      # Restart the script from top to process new queue items
