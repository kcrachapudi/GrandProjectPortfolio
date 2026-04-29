import streamlit as st
import subprocess
import threading
import time
import queue
from datetime import datetime

st.set_page_config(page_title="Portfolio Monitor", page_icon="🛰️", layout="wide")

APP_URLS = [
    "https://bioinform1.streamlit.app/",
    "https://bioinform2.streamlit.app/",
    "https://medistream-ai-ready-medical-imaging-pipeline.streamlit.app/",
    "https://smartcreditriskloaneligibilityengine.streamlit.app/",
    "https://stockmarketperformanceandforecastingengine.streamlit.app/",
    "https://real-timetransactionfrauddetectionsystem.streamlit.app/",
    "https://rad-kalyan-rachapudi-recruiter.streamlit.app/",
]

APP_LABELS = {
    "https://bioinform1.streamlit.app/": "BioInform 1",
    "https://bioinform2.streamlit.app/": "BioInform 2",
    "https://medistream-ai-ready-medical-imaging-pipeline.streamlit.app/": "MediStream AI",
    "https://smartcreditriskloaneligibilityengine.streamlit.app/": "Smart Credit Risk",
    "https://stockmarketperformanceandforecastingengine.streamlit.app/": "Stock Forecast",
    "https://real-timetransactionfrauddetectionsystem.streamlit.app/": "Fraud Detection",
    "https://rad-kalyan-rachapudi-recruiter.streamlit.app/": "Recruiter Portfolio",
}

STATUS_CONFIG = {
    "⏳ Pending":      {"bg": "#1e1e2e", "border": "#cc5500", "dot": "#ff6a00", "text": "#ff6a00", "label": "PENDING"},
    "🔍 Checking...":  {"bg": "#1a2535", "border": "#2a4a7a", "dot": "#4a8fd4", "text": "#7ab3e8", "label": "CHECKING"},
    "🔔 Waking...":    {"bg": "#2a1f00", "border": "#ccaa00", "dot": "#ffe600", "text": "#ffe600", "label": "ZZZ WAKING"},
    "✅ Awake":        {"bg": "#002a10", "border": "#00cc55", "dot": "#00ff66", "text": "#00ff66", "label": "AWAKE"},
    "✅ Woken":        {"bg": "#002a10", "border": "#00cc55", "dot": "#00ff66", "text": "#00ff66", "label": "WOKEN"},
    "❌ Error":        {"bg": "#2a0a0a", "border": "#7a2020", "dot": "#e24b4a", "text": "#f07070", "label": "ERROR"},
}

if "statuses" not in st.session_state:
    st.session_state.statuses = {url: "⏳ Pending" for url in APP_URLS}
if "running" not in st.session_state:
    st.session_state.running = False
if "log_queue" not in st.session_state:
    st.session_state.log_queue = queue.Queue()
if "logs" not in st.session_state:
    st.session_state.logs = []
if "last_run" not in st.session_state:
    st.session_state.last_run = None
if "error_messages" not in st.session_state:
    st.session_state.error_messages = {}
if "start_time" not in st.session_state:
    st.session_state.start_time = None


def parse_status(line, statuses):
    updated = dict(statuses)
    for url in APP_URLS:
        if url in line or url.rstrip("/") in line:
            ll = line.lower()
            if "genuinely awake" in ll:
                updated[url] = "✅ Awake"
            elif "detected zzz" in ll or "clicking wake" in ll:
                updated[url] = "🔔 Waking..."
            elif "wake signal sent" in ll:
                updated[url] = "✅ Woken"
            elif "error" in ll:
                updated[url] = "❌ Error"
                st.session_state.error_messages[url] = line
            elif "checking" in ll:
                updated[url] = "🔍 Checking..."
    return updated


def run_wake_script(log_q):
    proc = subprocess.Popen(
        ["python", "wake_apps.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in proc.stdout:
        stripped = line.rstrip()
        if stripped:
            log_q.put(stripped)
    proc.wait()
    log_q.put("__DONE__")


# ── styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Outfit:wght@400;600;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebarContent"] { display: none !important; }
.st-emotion-cache-1cypcdb { display: none !important; }

.mon-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #003a30;
}
.mon-title {
    font-family: Cambria, Georgia, serif;
    font-weight: bold;
    font-size: 2.8rem;
    letter-spacing: -1px;
    color: #00e5cc;
    margin: 0;
    line-height: 1;
}
.mon-title span {
    background: linear-gradient(90deg, #00e5cc, #00aaff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.mon-subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #007a6a;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 6px;
}
.mon-lastrun {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #007a6a;
    text-align: right;
    line-height: 1.6;
}

.app-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    margin-bottom: 1.5rem;
}

.app-card {
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid;
    position: relative;
    overflow: hidden;
    transition: transform 0.15s ease;
}
.app-card:hover { transform: translateY(-2px); }
.app-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0.7;
}

.card-label {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    color: #e0e0ff;
    margin-bottom: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.card-url {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    color: #7a7aaa;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 14px;
}
.card-footer {
    display: flex;
    align-items: center;
    gap: 8px;
}
.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.status-dot.pulse {
    animation: blink 1.3s ease-in-out infinite;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.25; }
}
.status-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 2px;
}

/* text_area styling */
div[data-testid="stTextArea"] label {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.65rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #00e5cc !important;
}
div[data-testid="stTextArea"] textarea {
    background: #ffffff !important;
    color: #006655 !important;
    border: 1px solid #00ccaa !important;
    border-radius: 10px !important;
    font-family: "IBM Plex Mono", monospace !important;
    font-size: 0.68rem !important;
    line-height: 1.9 !important;
}

.error-hint {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.58rem;
    color: #e24b4a;
    opacity: 0.7;
    margin-left: 6px;
    font-style: italic;
}

.section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #007a6a;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.log-wrap {
    background: #0a0f2e;
    border: 1px solid #1a2560;
    border-radius: 10px;
    padding: 14px 18px;
    height: 120px;
    overflow-y: auto;
}
.log-line {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #333355;
    line-height: 1.9;
}
.log-line.awake  { color: #1de9a0; }
.log-line.waking { color: #f5c060; }
.log-line.error  { color: #e24b4a; }
.log-line.check  { color: #4a8fd4; }
</style>
""", unsafe_allow_html=True)

# ── header ────────────────────────────────────────────────────────────────────
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

# ── button ────────────────────────────────────────────────────────────────────
btn_label = "⏳  Running..." if st.session_state.running else "🚀  Check / Wake All"
if st.button(btn_label, disabled=st.session_state.running):
    st.session_state.statuses = {url: "⏳ Pending" for url in APP_URLS}
    st.session_state.logs = []
    st.session_state.log_queue = queue.Queue()
    st.session_state.running = True
    st.session_state.start_time = time.time()
    st.session_state.error_messages = {}
    st.session_state.logs.append(f"🚀 Wake sequence started at {datetime.now().strftime('%H:%M:%S')} — checking {len(APP_URLS)} apps...")
    threading.Thread(
        target=run_wake_script,
        args=(st.session_state.log_queue,),
        daemon=True,
    ).start()

# ── timeout check (5 minutes) ────────────────────────────────────────────────
if st.session_state.running and st.session_state.start_time:
    if time.time() - st.session_state.start_time > 300:
        st.session_state.running = False
        st.session_state.logs.append("⚠️ Timed out after 5 minutes.")

# ── drain queue (always, not just when running) ───────────────────────────────
q = st.session_state.log_queue
while not q.empty():
    try:
        line = q.get_nowait()
        if line == "__DONE__":
            st.session_state.running = False
            st.session_state.last_run = datetime.now().strftime("%b %d %Y  %H:%M:%S")
        else:
            st.session_state.logs.append(line)
            st.session_state.statuses = parse_status(line, st.session_state.statuses)
    except:
        break

# ── inline log box ────────────────────────────────────────────────────────────
log_text = chr(10).join(st.session_state.logs[-60:]) if st.session_state.logs else ""
st.text_area("Log", value=log_text, height=120, disabled=True, placeholder="Log output will appear here...")

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ── cards grid ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Apps</div>', unsafe_allow_html=True)

cards_html = '<div class="app-grid">'
for url in APP_URLS:
    status = st.session_state.statuses[url]
    cfg = STATUS_CONFIG.get(status, STATUS_CONFIG["⏳ Pending"])
    label = APP_LABELS.get(url, url)
    pulse = "pulse" if status in ("🔍 Checking...", "🔔 Waking...") else ""
    error_msg = st.session_state.error_messages.get(url, "")
    tooltip_attr = 'title="' + error_msg.replace('"', "'") + '"' if error_msg else ""
    hint_span = '<span class="error-hint">hover for details</span>' if error_msg else ""
    bg = cfg['bg']
    border = cfg['border']
    accent = cfg['dot']
    dot_color = cfg['dot']
    status_label = cfg['label']
    status_text = cfg['text']
    cards_html += (
        f'<div class="app-card" style="background:{bg}; border-color:{border}; --accent:{accent};" {tooltip_attr}>'
        f'<div class="card-label">{label}</div>'
        f'<div class="card-url">{url}</div>'
        f'<div class="card-footer">'
        f'<div class="status-dot {pulse}" style="background:{dot_color};"></div>'
        f'<span class="status-label" style="color:{status_text};">{status_label}</span>'
        f'{hint_span}'
        f'</div></div>'
    )
cards_html += '</div>'
st.markdown(cards_html, unsafe_allow_html=True)

# ── auto-refresh while running ────────────────────────────────────────────────
if st.session_state.running:
    time.sleep(2)
    st.rerun()