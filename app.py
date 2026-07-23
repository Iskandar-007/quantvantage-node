"""
============================================================
S&P 500 Core Matrix - Portfolio Automation Dashboard
Version:  2.3.0  |  Date: 23 July 2026  |  "Premium Skin"
Framework: Streamlit 1.35+  |  Python 3.11+
Live Yahoo Finance data rendered through an institutional
dark theme: KPI tiles, allocation donut, milestone ladder,
rich cockpit cards (DCAX2 flash + milestone trim + sparkline),
and a premium sortable watchlist matrix.
============================================================
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import math

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

# Display ticker -> Yahoo Finance lookup symbol.
# SK Hynix trades on the Korea Exchange and needs the .KS suffix.
TICKER_MAP = {
    "KO": "KO",       "MSFT": "MSFT",   "PLTR": "PLTR",   "SIVR": "SIVR",
    "SKHY": "000660.KS", "V": "V",      "VZ": "VZ",       "AMZN": "AMZN",
    "GOOG": "GOOG",   "NVDA": "NVDA",   "BN": "BN",       "REXR": "REXR",
    "MELI": "MELI",   "NU": "NU",       "SOFI": "SOFI",   "AVGO": "AVGO",
    "INTC": "INTC",   "ALAB": "ALAB",   "AMD": "AMD",     "NKE": "NKE",
    "CAKE": "CAKE",   "HIMS": "HIMS",   "ARM": "ARM",     "ASML": "ASML",
    "MU": "MU",       "ANET": "ANET",   "CDNS": "CDNS",   "LRCX": "LRCX",
    "TSM": "TSM",     "VRT": "VRT",     "GEV": "GEV",     "CIEN": "CIEN",
    "BE": "BE",       "CEG": "CEG",     "DLR": "DLR",     "MDB": "MDB",
    "CRWD": "CRWD",   "TSLA": "TSLA",
}

SPY_TICKER = "SPY"
MAX_ACTIVE_STOCKS = 10
MILESTONE_LEVELS = [1.5, 2.0, 2.5, 3.0]   # +50%, +100%, +150%, +200%
DCAX2_THRESHOLD = -0.20                    # -20% from 52-week high

# Dollar sign as an HTML entity, so Streamlit never mistakes
# currency figures for LaTeX math (which would corrupt them).
DS = "&#" + "36;"
DIVIDER = '<div style="height:1px;background:#1e293b;margin:22px 0"></div>'

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="S&P 500 Core Matrix",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# PREMIUM THEME (injected CSS - dark institutional surfaces)
# ============================================================

PREMIUM_CSS = '''
<style>
.stApp { background:#020617; }
section[data-testid="stSidebar"] { background:#0b1220; }
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label { color:#cbd5e1; }
.stApp h1, .stApp h2, .stApp h3 { color:#f8fafc; letter-spacing:-0.01em; }
.stApp p, .stApp .stMarkdown { color:#cbd5e1; }
[data-testid="stMetric"] { background:#0f172a; border:1px solid #1e293b; border-radius:14px; padding:12px 14px; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { font-family:ui-monospace,'SF Mono',Menlo,monospace; color:#f8fafc; }
[data-testid="stMetric"] [data-testid="stMetricLabel"] { color:#94a3b8; }
.stButton>button { background:#0f172a; color:#e2e8f0; border:1px solid #334155; border-radius:10px; }
.stButton>button:hover { border-color:#10b981; color:#ffffff; }
details { background:#0f172a; border:1px solid #1e293b; border-radius:12px; }
.qvn-kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:6px 0 8px}
@media(max-width:900px){.qvn-kpi-grid{grid-template-columns:repeat(2,1fr)}}
.qvn-kpi{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:16px 18px;box-shadow:0 18px 48px -28px rgba(0,0,0,.7)}
.qvn-kpi-label{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#64748b}
.qvn-kpi-val{font-family:ui-monospace,'SF Mono',Menlo,monospace;font-size:24px;font-weight:700;color:#f8fafc;margin-top:6px}
.qvn-kpi-val.pos{color:#34d399}.qvn-kpi-val.neg{color:#fb7185}.qvn-kpi-val.amb{color:#fbbf24}
.qvn-kpi-sub{font-size:11px;color:#64748b;margin-top:4px;font-family:ui-monospace,monospace}
.qvn-card{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:16px;box-shadow:0 18px 48px -28px rgba(0,0,0,.7);min-height:340px;display:flex;flex-direction:column;gap:8px}
.qvn-card-head{display:flex;align-items:center;justify-content:space-between}
.qvn-ticker{font-family:ui-monospace,monospace;font-size:18px;font-weight:700;color:#ffffff}
.qvn-chip{font-family:ui-monospace,monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;background:#1e293b;color:#94a3b8;padding:2px 7px;border-radius:6px}
.qvn-price{font-family:ui-monospace,monospace;font-size:22px;font-weight:700;color:#ffffff}
.qvn-sub{font-size:11px;color:#64748b}
.qvn-pos{color:#34d399}.qvn-neg{color:#fb7185}
.qvn-meter{height:6px;background:#1e293b;border-radius:99px;overflow:hidden}
.qvn-meter-fill{height:100%;background:#475569;border-radius:99px;transition:width .5s}
.qvn-meter-amber{background:#f59e0b}
.qvn-row{display:flex;justify-content:space-between;font-size:12px;color:#94a3b8}
.qvn-row b{font-family:ui-monospace,monospace;color:#e2e8f0}
.qvn-banner-trim{margin-top:auto;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.4);border-radius:10px;padding:8px 10px;font-size:11px;font-weight:700;color:#6ee7b7;text-align:center}
.qvn-badge-dcax2{margin-top:auto;background:#f59e0b;border-radius:10px;padding:10px;font-size:11px;font-weight:800;letter-spacing:.02em;color:#0b1220;text-align:center;animation:qvnflash 1.1s ease-in-out infinite}
.qvn-nominal{margin-top:auto;background:#0b1220;border:1px solid #1e293b;border-radius:10px;padding:8px;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#64748b;text-align:center}
@keyframes qvnflash{0%,100%{opacity:1;box-shadow:0 0 22px -4px rgba(245,158,11,.8)}50%{opacity:.55;box-shadow:0 0 8px -4px rgba(245,158,11,.3)}}
.qvn-balance{display:flex;flex-direction:column;gap:10px}
.qvn-legend{display:flex;align-items:center;justify-content:space-between;border:1px solid;border-radius:12px;padding:12px 14px}
.qvn-leg-name{font-size:13px;font-weight:600;color:#ffffff}
.qvn-leg-desc{font-size:11px;color:#64748b}
.qvn-leg-val{font-family:ui-monospace,monospace;font-size:13px;font-weight:700;color:#ffffff}
.qvn-leg-pct{font-family:ui-monospace,monospace;font-size:11px}
.qvn-bar{display:flex;height:10px;border-radius:99px;overflow:hidden;background:#1e293b}
.qvn-ms-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.qvn-ms{background:#0b1220;border:1px solid #1e293b;border-radius:12px;padding:12px;text-align:center}
.qvn-ms.lit{background:rgba(16,185,129,.1);border-color:rgba(16,185,129,.45);box-shadow:0 0 30px -10px rgba(16,185,129,.5)}
.qvn-ms-l{font-family:ui-monospace,monospace;font-size:11px;font-weight:700;color:#64748b}
.qvn-ms.lit .qvn-ms-l{color:#6ee7b7}
.qvn-ms-v{font-family:ui-monospace,monospace;font-size:15px;font-weight:700;color:#cbd5e1;margin-top:2px}
.qvn-ms.lit .qvn-ms-v{color:#ffffff}
.qvn-ms-c{font-size:10px;color:#475569;margin-top:2px}
.qvn-ms.lit .qvn-ms-c{color:#34d399}
.qvn-table-wrap{max-height:520px;overflow:auto;border:1px solid #1e293b;border-radius:14px}
table.qvn-table{width:100%;border-collapse:collapse;font-size:13px}
table.qvn-table thead th{position:sticky;top:0;background:#0b1220;text-align:left;padding:12px 16px;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#64748b;border-bottom:1px solid #1e293b}
table.qvn-table td{padding:11px 16px;border-bottom:1px solid rgba(30,41,59,.6);color:#cbd5e1;font-family:ui-monospace,monospace}
table.qvn-table tr.qvn-trig{background:rgba(245,158,11,.06)}
.qvn-td-tk{color:#ffffff;font-weight:700}
.qvn-sig-dcax{background:rgba(245,158,11,.18);color:#fcd34d;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700}
.qvn-sig-base{background:#1e293b;color:#94a3b8;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700}
</style>
'''

def inject_premium_theme():
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# ============================================================
# CACHED DATA FETCH (1-year daily history for all symbols)
# ============================================================

@st.cache_data(ttl=3600, show_spinner="Fetching market data from Yahoo Finance...")
def fetch_market_data():
    symbols = list(TICKER_MAP.values()) + [SPY_TICKER]
    data = yf.download(
        tickers=symbols,
        period="1y",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )
    history, current_prices, high_52w = {}, {}, {}
    if data is None or data.empty:
        return history, pd.Series(dtype=float), pd.Series(dtype=float)
    for sym in symbols:
        try:
            df = data[sym].copy() if len(symbols) > 1 else data.copy()
            df.index = pd.to_datetime(df.index)
            df = df.dropna(how="all")
            if df.empty or "Close" not in df.columns:
                continue
            history[sym] = df
            current_prices[sym] = float(df["Close"].iloc[-1])
            high_52w[sym] = float(df["High"].max())
        except (KeyError, TypeError):
            continue
    return history, pd.Series(current_prices), pd.Series(high_52w)

def read_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return None

# ============================================================
# PREMIUM RENDER HELPERS (pure HTML/SVG - no extra libraries)
# ============================================================

def sparkline_svg(series, positive):
    vals = [float(v) for v in series.tail(30)]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    W, H = 120.0, 34.0
    pts = []
    for i, v in enumerate(vals):
        x = (i / (len(vals) - 1)) * W
        y = H - 2 - ((v - lo) / span) * (H - 4)
        pts.append(f"{x:.1f},{y:.1f}")
    color = "#10b981" if positive else "#fb7185"
    poly = " ".join(pts)
    return f'<svg viewBox="0 0 {W:.0f} {H:.0f}" preserveAspectRatio="none" style="width:100%;height:34px"><polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'

def donut_html(spx, active, dry):
    total = (spx + active + dry) or 1.0
    C = 2 * math.pi * 70
    segs = [(spx / total, "#10b981"), (active / total, "#0ea5e9"), (max(dry, 0) / total, "#f59e0b")]
    off = 0.0
    circ = ""
    for frac, color in segs:
        length = max(frac, 0.0) * C
        circ += f'<circle cx="100" cy="100" r="70" fill="none" stroke="{color}" stroke-width="22" stroke-dasharray="{length:.2f} {C - length:.2f}" stroke-dashoffset="{-off * C:.2f}"/>'
        off += frac
    return f'''<div style="position:relative;width:200px;height:200px;margin:0 auto">
<svg viewBox="0 0 200 200" style="transform:rotate(-90deg);width:200px;height:200px">
<circle cx="100" cy="100" r="70" fill="none" stroke="#1e293b" stroke-width="22"/>
{circ}
</svg>
<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">
<div style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#64748b">Total Value</div>
<div style="font-family:ui-monospace,monospace;font-size:18px;font-weight:700;color:#ffffff">{DS}{total:,.0f}</div>
</div></div>'''

def _leg(color, name, desc, val, pct):
    return f'<div class="qvn-legend" style="border-color:{color}33;background:{color}14"><div style="display:flex;align-items:center;gap:10px"><span style="width:12px;height:12px;border-radius:3px;background:{color}"></span><div><div class="qvn-leg-name">{name}</div><div class="qvn-leg-desc">{desc}</div></div></div><div style="text-align:right"><div class="qvn-leg-val">{val}</div><div class="qvn-leg-pct" style="color:{color}">{pct}</div></div></div>'

def legend_html(spx, active, dry):
    total = (spx + active + dry) or 1.0
    rows = [
        _leg("#10b981", "S&amp;P 500 Index Core", "Baseline anchor", f"{DS}{spx:,.2f}", f"{spx / total * 100:.1f}%"),
        _leg("#0ea5e9", "Active Stock Workspace", "DCAX2 operational slots", f"{DS}{active:
