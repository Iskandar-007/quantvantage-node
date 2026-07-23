"""
============================================================
S&P 500 Core Matrix - Portfolio Automation Dashboard
Version 3.0.0 - Phase A - 23 July 2026
Streamlit 1.35+ and Python 3.11+
Premium institutional terminal with: lazy page navigation,
restored Capital Recycling Engine (Execute Transfer), automated
DCAX2 Surveillance Feed, editable portfolio + CSV import,
per-stock Detail (fundamentals, analyst ratings, news),
custom tickers, watchlist, industry/theme map, coloured
keyword sentiment, and private user-held persistence.
All HTML is built from short string pieces so the source is
robust to copy and paste line wrapping.
============================================================
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import math
import json
import base64
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# Display ticker -> Yahoo Finance lookup symbol.
# SK Hynix trades on the Korea Exchange and needs .KS
TICKER_MAP = {
    "KO": "KO",
    "MSFT": "MSFT",
    "PLTR": "PLTR",
    "SIVR": "SIVR",
    "SKHY": "000660.KS",
    "V": "V",
    "VZ": "VZ",
    "AMZN": "AMZN",
    "GOOG": "GOOG",
    "NVDA": "NVDA",
    "BN": "BN",
    "REXR": "REXR",
    "MELI": "MELI",
    "NU": "NU",
    "SOFI": "SOFI",
    "AVGO": "AVGO",
    "INTC": "INTC",
    "ALAB": "ALAB",
    "AMD": "AMD",
    "NKE": "NKE",
    "CAKE": "CAKE",
    "HIMS": "HIMS",
    "ARM": "ARM",
    "ASML": "ASML",
    "MU": "MU",
    "ANET": "ANET",
    "CDNS": "CDNS",
    "LRCX": "LRCX",
    "TSM": "TSM",
    "VRT": "VRT",
    "GEV": "GEV",
    "CIEN": "CIEN",
    "BE": "BE",
    "CEG": "CEG",
    "DLR": "DLR",
    "MDB": "MDB",
    "CRWD": "CRWD",
    "TSLA": "TSLA",
}

# Industry / theme map (authored). Edit freely later.
THEME_MAP = {
    "KO": "Consumer Staples - Beverages",
    "MSFT": "AI - Software and Cloud",
    "PLTR": "AI - Orchestration and Data",
    "SIVR": "Precious Metals - Silver",
    "SKHY": "AI - Memory (HBM)",
    "V": "Fintech - Payments",
    "VZ": "Telecom",
    "AMZN": "AI - Cloud and Commerce",
    "GOOG": "AI - Search and Cloud",
    "NVDA": "AI - Compute (GPU)",
    "BN": "Financials - Diversified",
    "REXR": "Real Estate - Industrial",
    "MELI": "Fintech - LatAm Commerce",
    "NU": "Fintech - Digital Bank",
    "SOFI": "Fintech - Digital Bank",
    "AVGO": "AI - Networking and ASIC",
    "INTC": "AI - Compute (CPU and Foundry)",
    "ALAB": "AI - Connectivity (SerDes)",
    "AMD": "AI - Compute (GPU and CPU)",
    "NKE": "Consumer - Apparel",
    "CAKE": "Consumer - Restaurants",
    "HIMS": "Healthcare - Telehealth",
    "ARM": "AI - Compute (IP and Chips)",
    "ASML": "AI - Lithography Equipment",
    "MU": "AI - Memory",
    "ANET": "AI - Networking",
    "CDNS": "AI - EDA Software",
    "LRCX": "AI - Semi Equipment",
    "TSM": "AI - Foundry",
    "VRT": "AI - Power and Cooling",
    "GEV": "AI - Power Generation",
    "CIEN": "AI - Optical Networking",
    "BE": "AI - Power - Fuel Cells",
    "CEG": "AI - Power - Nuclear",
    "DLR": "Real Estate - Data Centers",
    "MDB": "AI - Data Software",
    "CRWD": "AI - Cybersecurity",
    "TSLA": "Embodied Robotics - EV and Autonomy",
}

SPY_TICKER = "SPY"
MAX_ACTIVE_STOCKS = 10
MILESTONE_LEVELS = [1.5, 2.0, 2.5, 3.0]
DCAX2_THRESHOLD = -0.20
PAGES = [
    "Command Center",
    "My Portfolio",
    "Stock Detail",
    "Global Matrix",
    "My Watchlist",
    "News and Sentiment",
    "Settings and Vault",
]

# Detail-view fundamentals. Edit this list to add or remove rows later.
FUND_FIELDS = [
    ("Market Cap", "marketCap", "usd0"),
    ("Trailing P/E", "trailingPE", "x2"),
    ("Forward P/E", "forwardPE", "x2"),
    ("Dividend Yield", "dividendYield", "pctfrac"),
    ("52-Week High", "fiftyTwoWeekHigh", "usd2"),
    ("52-Week Low", "fiftyTwoWeekLow", "usd2"),
    ("Beta (5Y)", "beta", "x2"),
    ("Trailing EPS", "trailingEps", "usd2"),
    ("Yahoo Sector", "sector", "str"),
    ("Yahoo Industry", "industry", "str"),
]

# Keyword sentiment lexicon (estimate only)
BULL_WORDS = set((
    "beat beats beating raise raises raised upgrade upgraded upgrades "
    "outperform record strong growth surge surges surged rally rallies "
    "gain gains profit profits breakthrough approval approved expansion "
    "bullish positive buy record-high accelerate accelerating"
).split())
BEAR_WORDS = set((
    "miss misses missed cut cuts downgrade downgraded downgrades "
    "underperform loss losses weak decline declines drop drops fell fall "
    "lawsuit investigation recall bearish negative sell warning layoff "
    "layoffs restructure default slump slow slowing"
).split())

# Dollar sign as an HTML entity so Streamlit never reads currency as math
DS = "&#" + "36;"

DIVIDER = (
    '<div style="height:1px;'
    'background:#1e293b;margin:20px 0"></div>'
)

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
# PREMIUM THEME CSS
# ============================================================

PREMIUM_CSS = '''
<style>
.stApp { background:#020617; }
section[data-testid="stSidebar"] { background:#0b1220; }
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label { color:#cbd5e1; }
.stApp h1, .stApp h2, .stApp h3 { color:#f8fafc; letter-spacing:-0.01em; }
.stApp p, .stApp .stMarkdown { color:#cbd5e1; }
[data-testid="stMetric"] {
  background:#0f172a; border:1px solid #1e293b;
  border-radius:14px; padding:12px 14px;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-family:ui-monospace,Menlo,monospace; color:#f8fafc;
}
[data-testid="stMetric"] [data-testid="stMetricLabel"] { color:#94a3b8; }
button[data-testid^="stBaseButton"] { border-radius:10px; }
button[data-testid="stBaseButton-secondary"] {
  background:#0f172a; color:#e2e8f0; border:1px solid #334155;
}
button[data-testid="stBaseButton-secondary"]:hover {
  border-color:#10b981; color:#fff;
}
button[data-testid="stBaseButton-primary"] {
  background:#10b981; color:#022c22; border:1px solid #10b981; font-weight:700;
}
button[data-testid="stBaseButton-primary"]:hover { background:#34d399; }
details { background:#0f172a; border:1px solid #1e293b; border-radius:12px; }
.qvn-brand { display:flex; align-items:center; gap:12px; margin:2px 0 10px; }
.qvn-nav { display:flex; gap:6px; flex-wrap:wrap; border-bottom:1px solid #1e293b; padding-bottom:10px; margin-bottom:6px; }
.qvn-kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:6px 0 8px; }
@media(max-width:900px){ .qvn-kpi-grid { grid-template-columns:repeat(2,1fr); } }
.qvn-kpi { background:#0f172a; border:1px solid #1e293b; border-radius:16px; padding:16px 18px; box-shadow:0 18px 48px -28px rgba(0,0,0,.7); }
.qvn-kpi-label { font-size:11px; text-transform:uppercase; letter-spacing:.12em; color:#64748b; }
.qvn-kpi-val { font-family:ui-monospace,Menlo,monospace; font-size:24px; font-weight:700; color:#f8fafc; margin-top:6px; }
.qvn-kpi-val.pos { color:#34d399; }
.qvn-kpi-val.neg { color:#fb7185; }
.qvn-kpi-val.amb { color:#fbbf24; }
.qvn-kpi-sub { font-size:11px; color:#64748b; margin-top:4px; font-family:ui-monospace,monospace; }
.qvn-card { background:#0f172a; border:1px solid #1e293b; border-radius:16px; padding:16px; box-shadow:0 18px 48px -28px rgba(0,0,0,.7); min-height:330px; display:flex; flex-direction:column; gap:8px; }
.qvn-card-head { display:flex; align-items:center; justify-content:space-between; }
.qvn-ticker { font-family:ui-monospace,monospace; font-size:18px; font-weight:700; color:#fff; }
.qvn-chip { font-family:ui-monospace,monospace; font-size:9px; letter-spacing:.1em; text-transform:uppercase; background:#1e293b; color:#94a3b8; padding:2px 7px; border-radius:6px; }
.qvn-theme { font-size:10px; color:#64748b; }
.qvn-price { font-family:ui-monospace,monospace; font-size:22px; font-weight:700; color:#fff; }
.qvn-sub { font-size:11px; color:#64748b; }
.qvn-pos { color:#34d399; }
.qvn-neg { color:#fb7185; }
.qvn-meter { height:6px; background:#1e293b; border-radius:99px; overflow:hidden; }
.qvn-meter-fill { height:100%; background:#475569; border-radius:99px; transition:width .5s; }
.qvn-meter-amber { background:#f59e0b; }
.qvn-row { display:flex; justify-content:space-between; font-size:12px; color:#94a3b8; }
.qvn-row b { font-family:ui-monospace,monospace; color:#e2e8f0; }
.qvn-banner-trim { margin-top:auto; background:rgba(16,185,129,.12); border:1px solid rgba(16,185,129,.4); border-radius:10px; padding:8px 10px; font-size:11px; font-weight:700; color:#6ee7b7; text-align:center; }
.qvn-badge-dcax2 { margin-top:auto; background:#f59e0b; border-radius:10px; padding:10px; font-size:11px; font-weight:800; letter-spacing:.02em; color:#0b1220; text-align:center; animation:qvnflash 1.1s ease-in-out infinite; }
.qvn-nominal { margin-top:auto; background:#0b1220; border:1px solid #1e293b; border-radius:10px; padding:8px; font-size:10px; letter-spacing:.12em; text-transform:uppercase; color:#64748b; text-align:center; }
@keyframes qvnflash { 0%,100% { opacity:1; box-shadow:0 0 22px -4px rgba(245,158,11,.8); } 50% { opacity:.55; box-shadow:0 0 8px -4px rgba(245,158,11,.3); } }
.qvn-balance { display:flex; flex-direction:column; gap:10px; }
.qvn-legend { display:flex; align-items:center; justify-content:space-between; border:1px solid; border-radius:12px; padding:12px 14px; }
.qvn-leg-name { font-size:13px; font-weight:600; color:#fff; }
.qvn-leg-desc { font-size:11px; color:#64748b; }
.qvn-leg-val { font-family:ui-monospace,monospace; font-size:13px; font-weight:700; color:#fff; }
.qvn-leg-pct { font-family:ui-monospace,monospace; font-size:11px; }
.qvn-bar { display:flex; height:10px; border-radius:99px; overflow:hidden; background:#1e293b; }
.qvn-ms-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.qvn-ms { background:#0b1220; border:1px solid #1e293b; border-radius:12px; padding:12px; text-align:center; }
.qvn-ms.lit { background:rgba(16,185,129,.1); border-color:rgba(16,185,129,.45); box-shadow:0 0 30px -10px rgba(16,185,129,.5); }
.qvn-ms-l { font-family:ui-monospace,monospace; font-size:11px; font-weight:700; color:#64748b; }
.qvn-ms.lit .qvn-ms-l { color:#6ee7b7; }
.qvn-ms-v { font-family:ui-monospace,monospace; font-size:15px; font-weight:700; color:#cbd5e1; margin-top:2px; }
.qvn-ms.lit .qvn-ms-v { color:#fff; }
.qvn-ms-c { font-size:10px; color:#475569; margin-top:2px; }
.qvn-ms.lit .qvn-ms-c { color:#34d399; }
.qvn-table-wrap { max-height:560px; overflow:auto; border:1px solid #1e293b; border-radius:14px; }
table.qvn-table { width:100%; border-collapse:collapse; font-size:13px; }
table.qvn-table thead th { position:sticky; top:0; background:#0b1220; text-align:left; padding:12px 16px; font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:#64748b; border-bottom:1px solid #1e293b; }
table.qvn-table td { padding:11px 16px; border-bottom:1px solid rgba(30,41,59,.6); color:#cbd5e1; font-family:ui-monospace,monospace; }
table.qvn-table tr.qvn-trig { background:rgba(245,158,11,.07); }
.qvn-td-tk { color:#fff; font-weight:700; }
.qvn-sig-dcax { background:rgba(245,158,11,.18); color:#fcd34d; padding:2px 8px; border-radius:6px; font-size:10px; font-weight:700; }
.qvn-sig-base { background:#1e293b; color:#94a3b8; padding:2px 8px; border-radius:6px; font-size:10px; font-weight:700; }
.qvn-surv { background:#0f172a; border:1px solid rgba(245,158,11,.4); border-radius:14px; padding:14px; }
.qvn-surv-dev { font-family:ui-monospace,monospace; font-weight:700; color:#fb7185; }
.qvn-news { border-left:3px solid #475569; padding:8px 12px; margin:6px 0; background:#0b1220; border-radius:0 10px 10px 0; }
.qvn-news.pos { border-left-color:#10b981; }
.qvn-news.neg { border-left-color:#fb7185; }
.qvn-news-title { color:#e2e8f0; font-weight:600; font-size:13px; }
.qvn-news-meta { font-size:11px; color:#64748b; margin-top:3px; }
.qvn-tag { display:inline-block; font-size:10px; font-weight:700; padding:1px 7px; border-radius:6px; margin-left:6px; }
.qvn-tag.pos { background:rgba(16,185,129,.18); color:#6ee7b7; }
.qvn-tag.neg { background:rgba(251,113,133,.18); color:#fda4af; }
.qvn-tag.neu { background:#1e293b; color:#94a3b8; }
.qvn-detail-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; }
.qvn-detail-cell { background:#0b1220; border:1px solid #1e293b; border-radius:10px; padding:10px 12px; }
.qvn-detail-k { font-size:10px; text-transform:uppercase; letter-spacing:.1em; color:#64748b; }
.qvn-detail-v { font-family:ui-monospace,monospace; font-size:14px; font-weight:700; color:#f8fafc; margin-top:3px; }
.qvn-rec { display:flex; gap:8px; flex-wrap:wrap; }
.qvn-rec-pill { background:#0b1220; border:1px solid #1e293b; border-radius:10px; padding:8px 12px; font-family:ui-monospace,monospace; font-size:12px; color:#cbd5e1; }
.qvn-rec-pill .up { color:#34d399; }
.qvn-rec-pill .dn { color:#fb7185; }
</style>
'''


def inject_premium_theme():
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# ============================================================
# NUMBER / TEXT FORMATTERS (short, no f-string format specs)
# ============================================================

def _f2(x):
    return "{:,.2f}".format(float(x))

def _f0(x):
    return "{:,.0f}".format(float(x))

def _p1(x):
    return "{:.1f}".format(float(x))

def _p2(x):
    return "{:.2f}".format(float(x))

def _pcti(x):
    return "{:.1%}".format(float(x))

def _psgn(x):
    return "{:+.1f}%".format(float(x))

def _usd0(x):
    return DS + "{:,.0f}".format(float(x))

def _sym_of(disp):
    return TICKER_MAP.get(disp, disp)

def _theme_of(disp):
    return THEME_MAP.get(disp, "Custom - User-defined")

def _ago(epoch):
    try:
        s = int(epoch)
        now = int(datetime.now().timestamp())
        d = max(0, now - s)
        if d < 3600:
            return str(max(1, d // 60)) + "m ago"
        if d < 86400:
            return str(d // 3600) + "h ago"
        return str(d // 86400) + "d ago"
    except Exception:
        return ""

def _sentiment(text):
    low = (text or "").lower()
    toks = set("".join(ch if ch.isalnum() else " " for ch in low).split())
    bull = len(toks & BULL_WORDS)
    bear = len(toks & BEAR_WORDS)
    if bull > bear:
        return "pos"
    if bear > bull:
        return "neg"
    return "neu"

# ============================================================
# CACHED DATA FETCHERS
# ============================================================

@st.cache_data(ttl=3600, show_spinner="Fetching market data from Yahoo Finance...")
def fetch_market_data(symbols):
    syms = list(symbols)
    data = yf.download(
        tickers=syms,
        period="1y",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )
    history = {}
    prices = {}
    highs = {}
    if data is None or data.empty:
        return history, prices, highs
    for sym in syms:
        try:
            if len(syms) > 1:
                df = data[sym].copy()
            else:
                df = data.copy()
            df.index = pd.to_datetime(df.index)
            df = df.dropna(how="all")
            if df.empty or "Close" not in df.columns:
                continue
            history[sym] = df
            prices[sym] = float(df["Close"].iloc[-1])
            highs[sym] = float(df["High"].max())
        except (KeyError, TypeError):
            continue
    return history, prices, highs


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_info(sym):
    try:
        info = yf.Ticker(sym).info or {}
        return dict(info)
    except Exception:
        return {}


def _norm_news(raw):
    out = []
    if not raw:
        return out
    for item in raw:
        try:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            pub = item.get("publisher")
            link = item.get("link")
            t = item.get("providerPublishTime")
            rel = item.get("relatedTickers") or []
            content = item.get("content")
            if not title and isinstance(content, dict):
                title = content.get("title")
                pub = pub or content.get("providerDisplayName")
                cu = content.get("canonicalUrl") or {}
                ct = content.get("clickThroughUrl") or {}
                link = link or cu.get("url") or ct.get("url")
            if title:
                out.append({
                    "title": title,
                    "pub": pub or "",
                    "link": link or "#",
                    "time": t,
                    "rel": rel,
                })
        except Exception:
            continue
    return out[:12]


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news(sym):
    try:
        raw = yf.Ticker(sym).news
        return _norm_news(raw)
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_recs(sym):
    res = {
        "key": None,
        "mean": None,
        "n": None,
        "counts": None,
        "deltas": None,
        "moves": [],
    }
    try:
        info = yf.Ticker(sym).info or {}
        res["key"] = info.get("recommendationKey")
        res["mean"] = info.get("recommendationMean")
        res["n"] = info.get("numberOfAnalystOpinions")
    except Exception:
        pass
    try:
        rdf = yf.Ticker(sym).recommendations
        if rdf is not None and not rdf.empty:
            cols = ["strongBuy", "buy", "hold", "sell", "strongSell"]
            cols = [c for c in cols if c in rdf.columns]
            last = rdf.iloc[-1]
            res["counts"] = {c: int(last[c]) for c in cols}
            if len(rdf) >= 2:
                prev = rdf.iloc[-2]
                res["deltas"] = {c: int(last[c] - prev[c]) for c in cols}
            else:
                res["deltas"] = {c: 0 for c in cols}
    except Exception:
        pass
    try:
        udf = yf.Ticker(sym).upgrades_downgrades
        if udf is not None and not udf.empty:
            recent = udf.tail(5).iloc[::-1]
            for idx, row in recent.iterrows():
                dstr = str(idx.date()) if hasattr(idx, "date") else str(idx)
                res["moves"].append({
                    "date": dstr,
                    "firm": str(row.get("Firm", "")),
                    "to": str(row.get("ToGrade", "")),
                    "frm": str(row.get("FromGrade", "")),
                    "action": str(row.get("Action", "")),
                })
    except Exception:
        pass
    return res

# ============================================================
# PERSISTENCE ADAPTER (private, user-held)
# Swap _apply_blob / _current_blob for a private Node or DB later.
# ============================================================

def _current_blob():
    return {
        "positions": st.session_state.get("active_positions", []),
        "watchlist": st.session_state.get("watchlist", []),
        "trimmed": st.session_state.get("trimmed", {}),
        "settled": st.session_state.get("settled", {}),
        "cash_adjust": float(st.session_state.get("cash_adjust", 0.0)),
        "etf_value": float(st.session_state.get("etf_value", 50000.0)),
        "cash_value": float(st.session_state.get("cash_value", 25000.0)),
    }


def _apply_blob(blob):
    st.session_state["active_positions"] = blob.get("positions", [])
    st.session_state["watchlist"] = blob.get("watchlist", [])
    st.session_state["trimmed"] = blob.get("trimmed", {})
    st.session_state["settled"] = blob.get("settled", {})
    st.session_state["cash_adjust"] = float(blob.get("cash_adjust", 0.0))
    st.session_state["etf_value"] = float(blob.get("etf_value", 50000.0))
    st.session_state["cash_value"] = float(blob.get("cash_value", 25000.0))
    st.session_state["_loaded"] = True


def _encode(blob):
    raw = json.dumps(blob, ensure_ascii=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode(text):
    text = (text or "").strip()
    raw = base64.urlsafe_b64decode(text.encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def _toggle_watch(disp):
    wl = list(st.session_state.get("watchlist", []))
    if disp in wl:
        wl.remove(disp)
    else:
        wl.append(disp)
    st.session_state["watchlist"] = wl

# ============================================================
# PREMIUM HTML BUILDERS
# ============================================================

def sparkline_svg(series, positive):
    vals = [float(v) for v in series.tail(30)]
    if len(vals) < 2:
        return ""
    lo = min(vals)
    hi = max(vals)
    span = (hi - lo) or 1.0
    W = 120.0
    H = 34.0
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = (i / (n - 1)) * W
        y = H - 2 - ((v - lo) / span) * (H - 4)
        pts.append(_p1(x) + "," + _p1(y))
    color = "#10b981" if positive else "#fb7185"
    poly = " ".join(pts)
    vb = "0 0 " + _p0_safe(W) + " " + _p0_safe(H)
    return (
        '<svg viewBox="' + vb + '" '
        + 'preserveAspectRatio="none" '
        + 'style="width:100%;height:34px">'
        + '<polyline points="' + poly + '" '
        + 'fill="none" stroke="' + color + '" '
        + 'stroke-width="2" stroke-linecap="round" '
        + 'stroke-linejoin="round"/></svg>'
    )


def _p0_safe(x):
    return "{:.0f}".format(float(x))


def donut_html(spx, active, dry):
    total = (spx + active + dry) or 1.0
    C = 2 * math.pi * 70
    segs = [
        (spx / total, "#10b981"),
        (active / total, "#0ea5e9"),
        (max(dry, 0) / total, "#f59e0b"),
    ]
    off = 0.0
    circ = ""
    for frac, color in segs:
        length = max(frac, 0.0) * C
        dash = _p2(length) + " " + _p2(C - length)
        doff = _p2(-off * C)
        circ += (
            '<circle cx="100" cy="100" r="70" '
            + 'fill="none" stroke="' + color + '" '
            + 'stroke-width="22" '
            + 'stroke-dasharray="' + dash + '" '
            + 'stroke-dashoffset="' + doff + '"/>'
        )
        off += frac
    center = (
        '<div style="position:absolute;inset:0;'
        + 'display:flex;flex-direction:column;'
        + 'align-items:center;justify-content:center">'
        + '<div style="font-size:10px;letter-spacing:.12em;'
        + 'text-transform:uppercase;color:#64748b">'
        + 'Total Value</div>'
        + '<div style="font-family:ui-monospace,monospace;'
        + 'font-size:18px;font-weight:700;color:#fff">'
        + _usd0(total) + '</div></div>'
    )
    return (
        '<div style="position:relative;'
        + 'width:200px;height:200px;margin:0 auto">'
        + '<svg viewBox="0 0 200 200" '
        + 'style="transform:rotate(-90deg);'
        + 'width:200px;height:200px">'
        + '<circle cx="100" cy="100" r="70" '
        + 'fill="none" stroke="#1e293b" '
        + 'stroke-width="22"/>'
        + circ + '</svg>' + center + '</div>'
    )


def _leg(color, name, desc, val, pct):
    return (
        '<div class="qvn-legend" '
        + 'style="border-color:' + color + '33;'
        + 'background:' + color + '14">'
        + '<div style="display:flex;'
        + 'align-items:center;gap:10px">'
        + '<span style="width:12px;height:12px;'
        + 'border-radius:3px;background:' + color + '"></span>'
        + '<div><div class="qvn-leg-name">' + name + '</div>'
        + '<div class="qvn-leg-desc">' + desc + '</div></div></div>'
        + '<div style="text-align:right">'
        + '<div class="qvn-leg-val">' + val + '</div>'
        + '<div class="qvn-leg-pct" style="color:' + color + '">'
        + pct + '</div></div></div>'
    )


def legend_html(spx, active, dry):
    total = (spx + active + dry) or 1.0
    spx_v = DS + _f2(spx)
    spx_p = "{:.1f}%".format(spx / total * 100)
    act_v = DS + _f2(active)
    act_p = "{:.1f}%".format(active / total * 100)
    dry_v = DS + _f2(dry)
    dry_p = "{:.1f}%".format(max(dry, 0) / total * 100)
    rows = [
        _leg("#10b981", "S&amp;P 500 Index Core",
             "Baseline anchor", spx_v, spx_p),
        _leg("#0ea5e9", "Active Stock Workspace",
             "Effective post-trim value", act_v, act_p),
        _leg("#f59e0b", "Dry Powder Buffer",
             "Base cash plus recycled", dry_v, dry_p),
    ]
    return '<div class="qvn-balance">' + "".join(rows) + '</div>'


def bar_html(spx, active, dry):
    total = (spx + active + dry) or 1.0
    a = _p1(spx / total * 100)
    b = _p1(active / total * 100)
    c = _p1(max(dry, 0) / total * 100)
    return (
        '<div style="margin-top:8px">'
        + '<div style="display:flex;justify-content:space-between;'
        + 'font-size:10px;letter-spacing:.1em;text-transform:uppercase;'
        + 'color:#64748b;margin-bottom:6px">'
        + '<span>Allocation Mix</span>'
        + '<span>Target 50 / 50</span></div>'
        + '<div class="qvn-bar">'
        + '<div style="width:' + a + '%;background:#10b981"></div>'
        + '<div style="width:' + b + '%;background:#0ea5e9"></div>'
        + '<div style="width:' + c + '%;background:#f59e0b"></div>'
        + '</div></div>'
    )


def kpi_grid_html(items):
    cards = ""
    for label, val, sub, cls in items:
        cards += (
            '<div class="qvn-kpi">'
            + '<div class="qvn-kpi-label">' + label + '</div>'
            + '<div class="qvn-kpi-val ' + cls + '">' + val + '</div>'
            + '<div class="qvn-kpi-sub">' + sub + '</div></div>'
        )
    return '<div class="qvn-kpi-grid">' + cards + '</div>'


def milestone_ladder_html(positions, prices):
    counts = {m: 0 for m in MILESTONE_LEVELS}
    settled = st.session_state.get("settled", {})
    for pos in positions:
        sym = _sym_of(pos["ticker"])
        cur = prices.get(sym)
        cost = pos["avg_cost"]
        if cur and cost > 0:
            mult = cur / cost
            settled_lvl = settled.get(pos["ticker"], 0.0)
            for m in MILESTONE_LEVELS:
                if mult >= m and m > settled_lvl:
                    counts[m] += 1
    cells = ""
    for i, m in enumerate(MILESTONE_LEVELS):
        lit = "lit" if counts[m] > 0 else ""
        gp = int((m - 1) * 100)
        cells += (
            '<div class="qvn-ms ' + lit + '">'
            + '<div class="qvn-ms-l">M' + str(i + 1) + '</div>'
            + '<div class="qvn-ms-v">+' + str(gp) + '%</div>'
            + '<div class="qvn-ms-c">' + str(counts[m]) + ' pending</div></div>'
        )
    return '<div class="qvn-ms-grid">' + cells + '</div>'


def _pos_metrics(pos, prices, highs):
    sym = _sym_of(pos["ticker"])
    cur = prices.get(sym)
    high = highs.get(sym)
    cost = pos["avg_cost"]
    shares = pos["shares"]
    trimmed = float(st.session_state.get("trimmed", {}).get(pos["ticker"], 0.0))
    gross = (shares * cur) if cur else 0.0
    eff = max(gross - trimmed, 0.0)
    drawdown = (cur - high) / high if (cur and high) else 0.0
    pnl_pct = (cur - cost) / cost * 100 if (cur and cost) else 0.0
    dcax = drawdown <= DCAX2_THRESHOLD
    milestone = None
    if cur and cost > 0:
        mult = cur / cost
        settled_lvl = st.session_state.get("settled", {}).get(pos["ticker"], 0.0)
        for m in MILESTONE_LEVELS:
            if mult >= m and m > settled_lvl:
                milestone = m
    return {
        "cur": cur,
        "high": high,
        "gross": gross,
        "eff": eff,
        "trimmed": trimmed,
        "drawdown": drawdown,
        "pnl_pct": pnl_pct,
        "dcax": dcax,
        "milestone": milestone,
        "cost": cost,
        "shares": shares,
    }


def cockpit_card_html(pos, m):
    positive = m["pnl_pct"] >= 0
    dd_sev = min(abs(m["drawdown"]) / 0.40, 1.0) * 100
    dev_cls = "qvn-neg" if m["drawdown"] < 0 else "qvn-pos"
    gain_cls = "qvn-pos" if positive else "qvn-neg"
    chip = "DCAX2" if m["dcax"] else "DCA"
    fill_cls = "qvn-meter-amber" if m["dcax"] else ""
    star = "★" if pos["ticker"] in st.session_state.get("watchlist", []) else "☆"
    banner = ""
    if m["milestone"]:
        gp = int((m["milestone"] - 1) * 100)
        banner = (
            '<div class="qvn-banner-trim">'
            + '&#128176; MILESTONE TRIM +' + str(gp)
            + '% &mdash; LOCK IN PROFITS</div>'
        )
    if m["dcax"]:
        alert = (
            '<div class="qvn-badge-dcax2">'
            + '&#9888;&#65039; DCAX2 TRIGGERED: '
            + 'DEPLOY 3x BUY SIZE</div>'
        )
    else:
        alert = (
            '<div class="qvn-nominal">'
            + 'Baseline DCA &middot; Within Tolerance</div>'
        )
    trimmed_line = ""
    if m["trimmed"] > 0:
        trimmed_line = (
            '<div class="qvn-row"><span>Trimmed to date</span><b>'
            + DS + _f2(m["trimmed"]) + '</b></div>'
        )
    head = (
        '<div class="qvn-card">'
        + '<div class="qvn-card-head">'
        + '<span class="qvn-ticker">' + pos["ticker"] + ' <span style="color:#fbbf24">' + star + '</span></span>'
        + '<span class="qvn-chip">' + chip + '</span></div>'
        + '<div class="qvn-theme">' + _theme_of(pos["ticker"]) + '</div>'
        + '<div class="qvn-price">' + (DS + _f2(m["cur"]) if m["cur"] else "N/A") + '</div>'
        + '<div class="qvn-sub">52W High ' + (DS + _f2(m["high"]) if m["high"] else "N/A")
        + ' &middot; Dev <span class="' + dev_cls + '">'
        + _pcti(m["drawdown"]) + '</span></div>'
    )
    meter = (
        '<div class="qvn-meter">'
        + '<div class="qvn-meter-fill ' + fill_cls
        + '" style="width:' + _p0_safe(dd_sev) + '%"></div></div>'
    )
    rows = (
        '<div class="qvn-row"><span>Shares</span><b>'
        + _f0(m["shares"]) + '</b></div>'
        + '<div class="qvn-row"><span>Avg Cost</span><b>'
        + DS + _f2(m["cost"]) + '</b></div>'
        + '<div class="qvn-row"><span>Value (post-trim)</span><b>'
        + DS + _f2(m["eff"]) + '</b></div>'
        + '<div class="qvn-row"><span>Gain vs cost</span>'
        + '<b class="' + gain_cls + '">' + _psgn(m["pnl_pct"]) + '</b></div>'
        + trimmed_line
    )
    return head + meter + rows + banner + alert + '</div>'


def surv_html(flagged):
    if not flagged:
        return (
            '<div class="qvn-card" style="min-height:auto">'
            + '<div class="qvn-sub">No asset in the universe is currently '
            + '20% or more below its 52-week high. The engine stays watchful; '
            + 'the amber feed lights up automatically the moment one qualifies.'
            + '</div></div>'
        )
    cards = ""
    for f in flagged:
        cards += (
            '<div class="qvn-surv">'
            + '<div class="qvn-card-head">'
            + '<span class="qvn-ticker">' + f["ticker"] + '</span>'
            + '<span class="qvn-surv-dev">' + _psgn(f["drawdown"] * 100) + '</span></div>'
            + '<div class="qvn-theme">' + f["theme"] + '</div>'
            + '<div class="qvn-sub">52W High ' + DS + _f2(f["high"])
            + ' &rarr; live ' + DS + _f2(f["cur"]) + '</div>'
            + '<div class="qvn-badge-dcax2" style="margin-top:10px">'
            + '&#9888;&#65039; DCAX2 SIGNAL: DEPLOY 3x CAPITAL MULTIPLIER</div>'
            + '</div>'
        )
    return (
        '<div style="display:grid;'
        + 'grid-template-columns:repeat(auto-fill,minmax(240px,1fr));'
        + 'gap:12px">' + cards + '</div>'
    )


def wl_row(r):
    dev = r["dev"]
    cls = "qvn-trig" if r["dcax"] else ""
    dev_cls = "qvn-neg" if (dev is not None and dev < 0) else "qvn-pos"
    dev_txt = _p1(dev) + "%" if dev is not None else "N/A"
    price_txt = DS + _f2(r["cur"]) if r["cur"] is not None else "N/A"
    high_txt = DS + _f2(r["high"]) if r["high"] is not None else "N/A"
    star = '<span style="color:#fbbf24">★</span> ' if r["starred"] else ""
    if r["dcax"]:
        sig = '<span class="qvn-sig-dcax">&#9888; DCAX2</span>'
    else:
        sig = '<span class="qvn-sig-base">Baseline</span>'
    return (
        '<tr class="' + cls + '">'
        + '<td class="qvn-td-tk">' + star + r["ticker"] + '</td>'
        + '<td style="color:#94a3b8;font-family:Inter,sans-serif;font-size:11px">' + r["theme"] + '</td>'
        + '<td>' + price_txt + '</td>'
        + '<td>' + high_txt + '</td>'
        + '<td class="' + dev_cls + '">' + dev_txt + '</td>'
        + '<td>' + sig + '</td></tr>'
    )


def watchlist_html(rows):
    if not rows:
        return (
            '<div class="qvn-table-wrap" '
            + 'style="padding:24px;text-align:center;color:#64748b">'
            + 'No assets match your filter.</div>'
        )
    head = (
        '<thead><tr><th>Ticker</th><th>Industry / Theme</th>'
        + '<th>Live Price</th><th>52-Week High</th>'
        + '<th>Deviation</th><th>Signal</th></tr></thead>'
    )
    body = "<tbody>" + "".join(wl_row(r) for r in rows) + "</tbody>"
    return (
        '<div class="qvn-table-wrap">'
        + '<table class="qvn-table">' + head + body + '</table></div>'
    )


def news_block(items):
    if not items:
        return '<div class="qvn-sub">No headlines available right now for this symbol.</div>'
    html = ""
    for it in items:
        s = _sentiment(it["title"])
        label = {"pos": "positive", "neg": "negative", "neu": "neutral"}[s]
        rel = _ago(it["time"])
        meta = (it["pub"] + (" &middot; " + rel if rel else "")).strip(" &middot; ")
        html += (
            '<div class="qvn-news ' + s + '">'
            + '<div class="qvn-news-title">'
            + '<a href="' + it["link"] + '" target="_blank" '
            + 'style="color:#e2e8f0;text-decoration:none">'
            + it["title"] + '</a>'
            + '<span class="qvn-tag ' + s + '">estimate: ' + label + '</span></div>'
            + '<div class="qvn-news-meta">' + meta + '</div></div>'
        )
    return html


def detail_grid_html(info):
    cells = ""
    for label, key, kind in FUND_FIELDS:
        v = info.get(key)
        if v is None or v == "":
            txt = "N/A"
        elif kind == "usd0":
            txt = _usd0(v)
        elif kind == "usd2":
            txt = DS + _f2(v)
        elif kind == "x2":
            txt = _f2(v)
        elif kind == "pctfrac":
            txt = "{:.2f}%".format(float(v) * 100)
        else:
            txt = str(v)
        cells += (
            '<div class="qvn-detail-cell">'
            + '<div class="qvn-detail-k">' + label + '</div>'
            + '<div class="qvn-detail-v">' + txt + '</div></div>'
        )
    return '<div class="qvn-detail-grid">' + cells + '</div>'


def recs_html(rec):
    parts = []
    parts.append(
        '<div class="qvn-sub">Consensus: <b style="color:#f8fafc">'
        + str(rec.get("key") or "N/A").upper() + '</b>'
        + (' &middot; mean ' + _f2(rec["mean"]) if rec.get("mean") else '')
        + (' &middot; ' + str(rec.get("n")) + ' analysts' if rec.get("n") else '')
        + '</div>'
    )
    if rec.get("counts"):
        labels = {
            "strongBuy": "Strong Buy",
            "buy": "Buy",
            "hold": "Hold",
            "sell": "Sell",
            "strongSell": "Strong Sell",
        }
        pills = ""
        for k, lab in labels.items():
            if k not in rec["counts"]:
                continue
            c = rec["counts"][k]
            d = (rec.get("deltas") or {}).get(k, 0)
            if d > 0:
                dstr = ' <span class="up">(+' + str(d) + ')</span>'
            elif d < 0:
                dstr = ' <span class="dn">(' + str(d) + ')</span>'
            else:
                dstr = ' <span style="color:#64748b">(0)</span>'
            pills += (
                '<div class="qvn-rec-pill">' + lab + ': '
                + str(c) + dstr + '</div>'
            )
        parts.append('<div class="qvn-rec" style="margin-top:8px">' + pills + '</div>')
    else:
        parts.append('<div class="qvn-sub" style="margin-top:6px">Detailed rating breakdown unavailable from the data source.</div>')
    if rec.get("moves"):
        moves = '<div class="qvn-sub" style="margin-top:10px">Recent analyst actions</div>'
        for mv in rec["moves"]:
            moves += (
                '<div class="qvn-news-meta" style="margin-top:2px">'
                + mv["date"] + ' &middot; ' + mv["firm"] + ' &middot; '
                + mv["action"] + ' ' + mv["frm"] + ' &rarr; ' + mv["to"]
                + '</div>'
            )
        parts.append(moves)
    return "".join(parts)

# ============================================================
# CSV PARSER
# ============================================================

def _find_col(cols, needles):
    for c in cols:
        low = c.lower()
        for n in needles:
            if n in low:
                return c
    return None


def _parse_csv(file):
    df = pd.read_csv(file)
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)
    tk = _find_col(cols, ["ticker", "symbol", "instrument", "conid"])
    sh = _find_col(cols, ["shares", "quantity", "qty", "units", "position"])
    co = _find_col(cols, ["avg", "cost", "basis", "purchase", "price"])
    if tk is None:
        return None, "Could not find a ticker/symbol column in the CSV."
    rows = []
    for _, r in df.iterrows():
        try:
            t = str(r[tk]).strip().upper()
            if not t or t == "NAN":
                continue
            s = float(r[sh]) if (sh and not pd.isna(r[sh])) else 0.0
            c = float(r[co]) if (co and not pd.isna(r[co])) else 0.0
            if s <= 0:
                continue
            rows.append({"ticker": t, "shares": s, "avg_cost": max(c, 0.01)})
        except Exception:
            continue
    if not rows:
        return None, "No usable position rows were found in the CSV."
    return rows, None

# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    inject_premium_theme()

    # ---- Restore from bookmark link (once per session) ----
    if not st.session_state.get("_loaded"):
        p = st.query_params.get("p")
        if p:
            try:
                _apply_blob(_decode(p))
            except Exception:
                pass

    # ---- Defaults for any state not yet set ----
    st.session_state.setdefault("active_positions", [])
    st.session_state.setdefault("watchlist", [])
    st.session_state.setdefault("trimmed", {})
    st.session_state.setdefault("settled", {})
    st.session_state.setdefault("cash_adjust", 0.0)
    st.session_state.setdefault("etf_value", 50000.0)
    st.session_state.setdefault("cash_value", 25000.0)
    st.session_state.setdefault("page", PAGES[0])

    positions = st.session_state["active_positions"]
    watchlist = st.session_state["watchlist"]

    # ---- Build symbol set (base + custom) ----
    custom = set()
    for pos in positions:
        if pos["ticker"] not in TICKER_MAP:
            custom.add(pos["ticker"].upper())
    for w in watchlist:
        if w not in TICKER_MAP:
            custom.add(w.upper())
    sym_list = list(TICKER_MAP.values()) + [SPY_TICKER] + sorted(custom)
    sym_tuple = tuple(sorted(set(sym_list)))

    history, prices, highs = fetch_market_data(sym_tuple)

    # ================= SIDEBAR =================
    with st.sidebar:
        st.title("🏦 Financial Housekeeping")
        st.markdown("---")
        st.subheader("Pre-Investment Gate")
        emergency_ok = st.checkbox(
            "6-12 month emergency cash buffer secured", value=True)
        debt_ok = st.checkbox(
            "0% high-interest non-mortgage debt", value=True)
        tax_ok = st.checkbox(
            "Tax-shield vehicles maximised (401k, IRA, HSA)", value=True)
        if emergency_ok and debt_ok and tax_ok:
            st.success("Gate cleared: deployment permitted")
        else:
            st.error("Gate closed: deploy only after all checks pass")
        st.markdown("---")
        st.subheader("Monthly Capital Split")
        etf_pct = st.slider(
            "S&P 500 ETF Allocation (%)",
            min_value=0, max_value=100, value=50, step=5,
            help="Percentage routed to SPY. Remainder to dry powder pool.",
        )
        ca, cb = st.columns(2)
        ca.metric("SPY Allocation", str(etf_pct) + "%")
        cb.metric("Dry Powder Pool", str(100 - etf_pct) + "%")
        st.markdown("---")
        st.subheader("Portfolio Snapshot")
        etf_value = st.number_input(
            "Current S&P 500 / ETF value",
            min_value=0.0, step=1000.0, key="etf_value")
        cash_value = st.number_input(
            "Base cash reserve (manual)",
            min_value=0.0, step=1000.0, key="cash_value")
        st.caption(
            "These are your manual snapshots. The Capital Recycling "
            "Engine tracks its own trims on top of the base cash.")
        st.markdown("---")
        st.subheader("🔐 Broker Integration")
        try:
            ib = st.secrets["IBKR_TOKEN"]
            st.success("IBKR token sealed in vault")
        except Exception:
            st.info("Add IBKR_TOKEN to secrets later")
        try:
            t2 = st.secrets["T212_TOKEN"]
            st.success("Trading 212 token sealed in vault")
        except Exception:
            st.info("Add T212_TOKEN to secrets later")
        st.markdown("---")
        st.caption("Data from Yahoo Finance. Not financial advice.")

    # ================= BRAND + NAV =================
    st.markdown(
        '<div class="qvn-brand">'
        + '<svg viewBox="0 0 32 32" width="34" height="34">'
        + '<rect x="1.5" y="1.5" width="29" height="29" rx="8" '
        + 'fill="rgba(16,185,129,.1)" stroke="rgba(16,185,129,.5)" stroke-width="1.5"/>'
        + '<path d="M9 22 L16 9 L23 22" stroke="#34d399" stroke-width="2.2" '
        + 'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        + '<circle cx="16" cy="9" r="2.6" fill="#34d399"/></svg>'
        + '<div><div style="font-size:18px;font-weight:800;color:#fff">'
        + 'QuantVantage <span style="color:#34d399">Node</span></div>'
        + '<div style="font-family:ui-monospace,monospace;font-size:10px;'
        + 'letter-spacing:.18em;text-transform:uppercase;color:#64748b">'
        + 'Operator Console v3.0</div></div></div>',
        unsafe_allow_html=True,
    )

    nav_cols = st.columns(len(PAGES))
    for i, pg in enumerate(PAGES):
        with nav_cols[i]:
            if st.button(
                pg,
                key="nav_" + pg,
                type=("primary" if st.session_state["page"] == pg else "secondary"),
                use_container_width=True,
            ):
                st.session_state["page"] = pg
                st.rerun()

    page = st.session_state["page"]

    # ---- Shared derived values ----
    cash_adjust = float(st.session_state["cash_adjust"])
    dry_powder = cash_value + cash_adjust

    total_stock_eff = 0.0
    total_stock_gross = 0.0
    cost_basis = 0.0
    metrics_by_disp = {}
    for pos in positions:
        m = _pos_metrics(pos, prices, highs)
        metrics_by_disp[pos["ticker"]] = m
        total_stock_eff += m["eff"]
        total_stock_gross += m["gross"]
        cost_basis += m["shares"] * m["cost"]
    total_portfolio = etf_value + total_stock_eff + dry_powder
    unrealized = total_stock_eff - cost_basis

    # ================= PAGE: COMMAND CENTER =================
    if page == "Command Center":
        st.markdown("## Command Center")

        st.markdown(
            kpi_grid_html([
                ("Net Liquidation Value", DS + _f2(total_portfolio),
                 "ETF plus active plus dry powder", "pos"),
                ("Unrealized P&L (Active)", (DS + _f2(unrealized)),
                 "Effective post-trim vs cost",
                 ("pos" if unrealized >= 0 else "neg")),
                ("Active DCAX2 Signals",
                 str(sum(1 for m in metrics_by_disp.values() if m["dcax"])),
                 "Among your holdings", "amb"),
                ("Dry Powder Ratio",
                 "{:.1f}%".format(dry_powder / total_portfolio * 100 if total_portfolio else 0),
                 "Base cash plus recycled", "amb"),
            ]),
            unsafe_allow_html=True,
        )

        st.markdown(DIVIDER, unsafe_allow_html=True)

        c1, c2 = st.columns([3, 2])
        with c1:
            st.subheader("🧭 Core Balance Tracker")
            st.markdown(
                '<div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center">'
                + donut_html(etf_value, total_stock_eff, dry_powder)
                + '<div style="flex:1;min-width:240px">'
                + legend_html(etf_value, total_stock_eff, dry_powder)
                + bar_html(etf_value, total_stock_eff, dry_powder)
                + '</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.subheader("♻️ Capital Recycling Engine")
            st.markdown(
                milestone_ladder_html(positions, prices),
                unsafe_allow_html=True,
            )
            st.caption(
                "Crossing +50 / +100 / +150 / +200% arms a trim. "
                "Execute it below to lock the profit into Dry Powder.")

        st.markdown(DIVIDER, unsafe_allow_html=True)

        # ---- Trim queue with Execute Transfer ----
        st.subheader("Trim Event Queue")
        pending = []
        settled_rows = []
        for pos in positions:
            m = metrics_by_disp[pos["ticker"]]
            if m["milestone"]:
                rate = {1.5: 0.10, 2.0: 0.15, 2.5: 0.20, 3.0: 0.25}[m["milestone"]]
                amt = m["eff"] * rate
                pending.append((pos["ticker"], m["milestone"], amt))
            lvl = st.session_state.get("settled", {}).get(pos["ticker"], 0.0)
            if lvl > 0:
                settled_rows.append((pos["ticker"], lvl, m["trimmed"]))

        if pending:
            pc = st.columns(2)
            for i, (tk, lvl, amt) in enumerate(pending):
                gp = int((lvl - 1) * 100)
                with pc[i % 2]:
                    st.markdown(
                        '<div class="qvn-card" style="min-height:auto">'
                        + '<div class="qvn-card-head"><span class="qvn-ticker">' + tk + '</span>'
                        + '<span class="qvn-chip">M' + str(MILESTONE_LEVELS.index(lvl) + 1)
                        + ' &middot; +' + str(gp) + '%</span></div>'
                        + '<div class="qvn-banner-trim" style="margin-top:8px">'
                        + '&#128176; MILESTONE TRIM REACHED: '
                        + 'TRANSFER PROFITS TO DRY POWDER BUFFER</div>'
                        + '<div class="qvn-row" style="margin-top:8px"><span>Trim amount</span><b>'
                        + DS + _f2(amt) + '</b></div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Execute Transfer",
                        key="exec_" + tk + "_" + str(lvl),
                        type="primary",
                        use_container_width=True,
                    ):
                        tr = dict(st.session_state.get("trimmed", {}))
                        tr[tk] = float(tr.get(tk, 0.0)) + amt
                        st.session_state["trimmed"] = tr
                        st.session_state["cash_adjust"] = cash_adjust + amt
                        se = dict(st.session_state.get("settled", {}))
                        se[tk] = max(float(se.get(tk, 0.0)), lvl)
                        st.session_state["settled"] = se
                        st.success(
                            "Transferred " + DS + _f2(amt)
                            + " from " + tk + " into the Dry Powder Buffer.")
                        st.rerun()
        else:
            st.info(
                "No milestone is currently armed on your holdings. "
                "The ladder above lights up the moment one qualifies.")

        if settled_rows:
            st.caption("Settled trims")
            for tk, lvl, tr in settled_rows:
                gp = int((lvl - 1) * 100)
                st.markdown(
                    '<div class="qvn-row" style="padding:4px 0">'
                    + '<span><b style="color:#e2e8f0">' + tk + '</b> '
                    + '&mdash; M' + str(MILESTONE_LEVELS.index(lvl) + 1)
                    + ' (+' + str(gp) + '%) settled</span>'
                    + '<b style="color:#34d399">' + DS + _f2(tr) + ' recycled</b></div>',
                    unsafe_allow_html=True,
                )

        st.markdown(
            '<div class="qvn-row" style="margin-top:10px;background:#0b1220;'
            + 'border:1px solid #1e293b;border-radius:10px;padding:10px 12px">'
            + '<span>Total capital recycled to buffer</span>'
            + '<b style="color:#34d399">' + DS + _f2(cash_adjust) + '</b></div>',
            unsafe_allow_html=True,
        )

        st.markdown(DIVIDER, unsafe_allow_html=True)

        # ---- Automated DCAX2 surveillance over the whole universe ----
        st.subheader("🛰️ DCAX2 Surveillance Feed (auto-scanned)")
        st.caption(
            "Scans every asset in the universe each refresh and flags "
            "anything 20% or more below its 52-week high. No manual adding needed.")
        flagged = []
        for disp in list(TICKER_MAP.keys()) + sorted(custom):
            sym = _sym_of(disp)
            cur = prices.get(sym)
            high = highs.get(sym)
            if cur and high:
                dd = (cur - high) / high
                if dd <= DCAX2_THRESHOLD:
                    flagged.append({
                        "ticker": disp,
                        "cur": cur,
                        "high": high,
                        "drawdown": dd,
                        "theme": _theme_of(disp),
                    })
        flagged.sort(key=lambda x: x["drawdown"])
        st.markdown(surv_html(flagged), unsafe_allow_html=True)

    # ================= PAGE: MY PORTFOLIO =================
    elif page == "My Portfolio":
        st.markdown(
            "## 🎯 Active Single-Stock Workspace ("
            + str(len(positions)) + " / " + str(MAX_ACTIVE_STOCKS) + " slots)")

        if len(positions) < MAX_ACTIVE_STOCKS:
            with st.expander("➕ Add a position (pick a stock or type any ticker)", expanded=False):
                with st.form("add_position_form", clear_on_submit=True):
                    mode = st.radio(
                        "Source",
                        ["From the 38-asset universe", "Type a custom ticker"],
                        horizontal=True,
                    )
                    new_ticker = None
                    if mode == "From the 38-asset universe":
                        held = [p["ticker"] for p in positions]
                        opts = [t for t in TICKER_MAP if t not in held]
                        new_ticker = st.selectbox(
                            "Select ticker", options=opts, index=None,
                            placeholder="Choose a stock...")
                    else:
                        raw = st.text_input(
                            "Ticker symbol (e.g. TLT, GLD, IAU)", "")
                        new_ticker = raw.strip().upper() or None
                    avg_cost = st.number_input(
                        "Average cost per share",
                        min_value=0.01, value=100.0, step=1.0)
                    shares = st.number_input(
                        "Number of shares",
                        min_value=0.0, value=1.0, step=1.0)
                    if st.form_submit_button("Add to Cockpit", type="primary") and new_ticker:
                        st.session_state["active_positions"].append({
                            "ticker": new_ticker,
                            "avg_cost": float(avg_cost),
                            "shares": float(shares),
                        })
                        st.rerun()
        else:
            st.warning("Maximum 10 active positions reached. Remove one first.")

        if positions:
            for row_start in range(0, len(positions), 3):
                row = positions[row_start:row_start + 3]
                cols = st.columns(3)
                for i, pos in enumerate(row):
                    idx = row_start + i
                    m = metrics_by_disp.get(pos["ticker"])
                    with cols[i]:
                        if m is None or m["cur"] is None or m["high"] is None:
                            st.markdown(
                                '<div class="qvn-card"><div class="qvn-ticker">'
                                + pos["ticker"] + '</div>'
                                + '<div class="qvn-sub">Market data unavailable '
                                + '(check the symbol spelling).</div></div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                cockpit_card_html(pos, m),
                                unsafe_allow_html=True,
                            )
                        b1, b2, b3, b4 = st.columns(4)
                        in_wl = pos["ticker"] in watchlist
                        with b1:
                            if st.button(
                                ("★" if in_wl else "☆"),
                                key="star_p_" + str(idx),
                                help="Toggle watchlist",
                                use_container_width=True,
                            ):
                                _toggle_watch(pos["ticker"])
                                st.rerun()
                        with b2:
                            if st.button(
                                "Detail",
                                key="det_p_" + str(idx),
                                use_container_width=True,
                            ):
                                st.session_state["detail_ticker"] = pos["ticker"]
                                st.session_state["page"] = "Stock Detail"
                                st.rerun()
                        with b3:
                            edit_key = "edit_p_" + str(idx)
                            if st.button(
                                "Edit",
                                key=edit_key,
                                use_container_width=True,
                            ):
                                st.session_state["editing"] = idx
                                st.rerun()
                        with b4:
                            if st.button(
                                "Remove",
                                key="rem_p_" + str(idx),
                                use_container_width=True,
                            ):
                                st.session_state["active_positions"].pop(idx)
                                st.rerun()

                        if st.session_state.get("editing") == idx:
                            with st.form("edit_form_" + str(idx)):
                                ec = st.number_input(
                                    "Average cost",
                                    min_value=0.01,
                                    value=float(pos["avg_cost"]),
                                    step=0.5,
                                    key="ec_" + str(idx))
                                es = st.number_input(
                                    "Shares",
                                    min_value=0.0,
                                    value=float(pos["shares"]),
                                    step=1.0,
                                    key="es_" + str(idx))
                                s1, s2 = st.columns(2)
                                with s1:
                                    save = st.form_submit_button(
                                        "Save", type="primary")
                                with s2:
                                    cancel = st.form_submit_button("Cancel")
                                if save:
                                    st.session_state["active_positions"][idx]["avg_cost"] = float(ec)
                                    st.session_state["active_positions"][idx]["shares"] = float(es)
                                    st.session_state["editing"] = None
                                    st.rerun()
                                if cancel:
                                    st.session_state["editing"] = None
                                    st.rerun()
        else:
            st.info("No active positions yet. Use the form above to add up to 10 stocks.")

    # ================= PAGE: STOCK DETAIL =================
    elif page == "Stock Detail":
        st.markdown("## 🔍 Stock Detail")
        all_disp = list(dict.fromkeys(
            [p["ticker"] for p in positions]
            + watchlist
            + list(TICKER_MAP.keys())
            + sorted(custom)
        ))
        default_det = st.session_state.get("detail_ticker") or (all_disp[0] if all_disp else None)
        if default_det not in all_disp and all_disp:
            default_det = all_disp[0]
        chosen = st.selectbox(
            "Select a stock to inspect",
            options=all_disp,
            index=(all_disp.index(default_det) if default_det in all_disp else 0),
            key="detail_select",
        )
        st.session_state["detail_ticker"] = chosen
        sym = _sym_of(chosen)
        cur = prices.get(sym)
        high = highs.get(sym)

        if cur is None or high is None:
            st.error("No market data for " + chosen + ". The symbol may be invalid.")
        else:
            dd = (cur - high) / high
            dcax = dd <= DCAX2_THRESHOLD
            h1, h2, h3, h4 = st.columns(4)
            h1.metric("Live Price", DS + _f2(cur))
            h2.metric("52-Week High", DS + _f2(high))
            h3.metric("Deviation", _pcti(dd))
            h4.metric("Theme", _theme_of(chosen)[:18])
            if dcax:
                st.error("⚠️ DCAX2 TRIGGERED: DEPLOY 3x BUY SIZE")
            else:
                st.info("Baseline DCA - within tolerance band")

            if sym in history:
                st.area_chart(history[sym]["Close"].tail(90), height=220)

            sb1, sb2 = st.columns(2)
            with sb1:
                in_wl = chosen in watchlist
                if st.button(
                    ("★ Remove from Watchlist" if in_wl else "☆ Add to Watchlist"),
                    key="star_detail",
                    type=("secondary" if in_wl else "primary"),
                ):
                    _toggle_watch(chosen)
                    st.rerun()
            with sb2:
                if st.button("🔄 Refresh this stock", key="ref_detail"):
                    fetch_info.clear()
                    fetch_news.clear()
                    fetch_recs.clear()
                    st.rerun()

            st.markdown(DIVIDER, unsafe_allow_html=True)
            st.subheader("Fundamentals")
            info = fetch_info(sym)
            st.markdown(detail_grid_html(info), unsafe_allow_html=True)

            st.markdown(DIVIDER, unsafe_allow_html=True)
            st.subheader("Analyst Ratings")
            rec = fetch_recs(sym)
            st.markdown(recs_html(rec), unsafe_allow_html=True)

            st.markdown(DIVIDER, unsafe_allow_html=True)
            st.subheader("Recent Headlines (sentiment = estimate)")
            st.markdown(news_block(fetch_news(sym)), unsafe_allow_html=True)

    # ================= PAGE: GLOBAL MATRIX =================
    elif page == "Global Matrix":
        st.markdown("## 🌍 Global Matrix Watchlist")
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
        with fc1:
            search = st.text_input("Search ticker", "", key="mx_search")
        with fc2:
            theme_opts = ["All themes"] + sorted(set(THEME_MAP.values()) | {"Custom - User-defined"})
            theme_f = st.selectbox("Theme filter", theme_opts, key="mx_theme")
        with fc3:
            sig_f = st.selectbox(
                "Signal filter",
                ["All signals", "DCAX2 only", "Baseline only"],
                key="mx_sig")
        with fc4:
            sort_f = st.selectbox(
                "Sort by",
                ["Deviation (deepest discount first)", "Ticker A-Z", "Theme A-Z"],
                key="mx_sort")

        rows = []
        for disp in list(TICKER_MAP.keys()) + sorted(custom):
            sym = _sym_of(disp)
            cur = prices.get(sym)
            high = highs.get(sym)
            if cur is None or high is None:
                dev = None
                dcax = False
            else:
                dev = (cur - high) / high * 100
                dcax = dev <= DCAX2_THRESHOLD * 100
            rows.append({
                "ticker": disp,
                "theme": _theme_of(disp),
                "cur": cur,
                "high": high,
                "dev": dev,
                "dcax": dcax,
                "starred": disp in watchlist,
            })

        s = search.strip().upper()
        if s:
            rows = [r for r in rows if s in r["ticker"]]
        if theme_f != "All themes":
            rows = [r for r in rows if r["theme"] == theme_f]
        if sig_f == "DCAX2 only":
            rows = [r for r in rows if r["dcax"]]
        elif sig_f == "Baseline only":
            rows = [r for r in rows if (r["dev"] is not None and not r["dcax"])]
        if sort_f == "Ticker A-Z":
            rows.sort(key=lambda r: r["ticker"])
        elif sort_f == "Theme A-Z":
            rows.sort(key=lambda r: (r["theme"], r["ticker"]))
        else:
            rows.sort(key=lambda r: (r["dev"] if r["dev"] is not None else 9999))

        st.markdown(watchlist_html(rows), unsafe_allow_html=True)
        st.caption(
            "★ = in your watchlist. Amber rows are DCAX2 buy candidates. "
            "Add or remove stars from the Stock Detail or My Watchlist pages.")

    # ================= PAGE: MY WATCHLIST =================
    elif page == "My Watchlist":
        st.markdown("## ⭐ My Watchlist")
        with st.expander("➕ Add a ticker to your watchlist", expanded=(len(watchlist) == 0)):
            with st.form("wl_add_form", clear_on_submit=True):
                wl_mode = st.radio(
                    "Source",
                    ["From the universe", "Type a custom ticker"],
                    horizontal=True,
                    key="wl_mode")
                pick = None
                if wl_mode == "From the universe":
                    pick = st.selectbox(
                        "Select ticker",
                        options=[t for t in TICKER_MAP if t not in watchlist],
                        index=None,
                        placeholder="Choose...",
                        key="wl_pick")
                else:
                    raw = st.text_input("Ticker symbol", "", key="wl_raw")
                    pick = raw.strip().upper() or None
                if st.form_submit_button("Add ★", type="primary") and pick:
                    if pick not in watchlist:
                        st.session_state["watchlist"].append(pick)
                    st.rerun()

        if watchlist:
            rows = []
            for disp in watchlist:
                sym = _sym_of(disp)
                cur = prices.get(sym)
                high = highs.get(sym)
                dev = ((cur - high) / high * 100) if (cur and high) else None
                dcax = (dev is not None and dev <= DCAX2_THRESHOLD * 100)
                rows.append({
                    "ticker": disp,
                    "theme": _theme_of(disp),
                    "cur": cur,
                    "high": high,
                    "dev": dev,
                    "dcax": dcax,
                    "starred": True,
                })
            st.markdown(watchlist_html(rows), unsafe_allow_html=True)
            st.markdown("##### Manage")
            for disp in list(watchlist):
                c1, c2 = st.columns([4, 1])
                with c1:
                    sym = _sym_of(disp)
                    cur = prices.get(sym)
                    st.markdown(
                        '<div class="qvn-row" style="padding:6px 0">'
                        + '<span><b style="color:#fff">' + disp + '</b> '
                        + '<span style="color:#64748b">' + _theme_of(disp) + '</span></span>'
                        + '<b style="color:#e2e8f0">' + (DS + _f2(cur) if cur else "N/A") + '</b></div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("Remove", key="wl_rm_" + disp):
                        _toggle_watch(disp)
                        st.rerun()
        else:
            st.info("Your watchlist is empty. Star stocks from the Matrix or Detail pages, or add one above.")

    # ================= PAGE: NEWS AND SENTIMENT =================
    elif page == "News and Sentiment":
        st.markdown("## 📰 News and Sentiment")
        st.caption(
            "Colours are a keyword-based estimate (green = positive, "
            "red = negative, grey = neutral), not a trading verdict.")
        scope = st.radio(
            "Feed scope",
            ["My holdings only", "Entire universe (slower, cached)"],
            horizontal=True,
            key="news_scope")

        if scope == "My holdings only":
            targets = [p["ticker"] for p in positions]
            if not targets:
                st.info("Add a holding first, or switch to the entire universe.")
                targets = []
            auto_load = True
        else:
            targets = list(TICKER_MAP.keys()) + sorted(custom)
            auto_load = st.session_state.get("news_universe_go", False)
            if not auto_load:
                if st.button("Load universe news (one-time, then cached)", type="primary"):
                    st.session_state["news_universe_go"] = True
                    st.rerun()

        if targets and (scope == "My holdings only" or auto_load):
            any_news = False
            for disp in targets:
                sym = _sym_of(disp)
                items = fetch_news(sym)
                if not items:
                    continue
                any_news = True
                st.markdown("##### " + disp + "  " + '<span style="color:#64748b;font-weight:400;font-size:12px">' + _theme_of(disp) + '</span>', unsafe_allow_html=True)
                st.markdown(news_block(items), unsafe_allow_html=True)
            if not any_news:
                st.info("No headlines returned right now. Yahoo's feed is unofficial and can be empty; try the Refresh button on Stock Detail later, or wait for the cache to renew.")
            if st.button("🔄 Refresh news cache", key="news_refresh"):
                fetch_news.clear()
                st.rerun()

    # ================= PAGE: SETTINGS AND VAULT =================
    elif page == "Settings and Vault":
        st.markdown("## ⚙️ Settings and Vault")

        st.subheader("Editable Portfolio Table")
        st.caption("Make small changes here directly. Add rows at the bottom; clear a row's ticker to delete it.")
        if positions:
            ed_df = pd.DataFrame(positions, columns=["ticker", "shares", "avg_cost"])
        else:
            ed_df = pd.DataFrame(columns=["ticker", "shares", "avg_cost"])
        edited = st.data_editor(
            ed_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "shares": st.column_config.NumberColumn("Shares", min_value=0.0, step=1.0),
                "avg_cost": st.column_config.NumberColumn("Avg Cost", min_value=0.0, step=0.5),
            },
            key="manual_editor",
        )
        if st.button("Save table edits", type="primary", key="save_editor"):
            new_pos = []
            for _, r in edited.iterrows():
                try:
                    tk = str(r["ticker"]).strip().upper()
                    sh = r["shares"]
                    co = r["avg_cost"]
                    if not tk or tk == "NAN":
                        continue
                    if pd.isna(sh) or pd.isna(co):
                        continue
                    if float(sh) <= 0 or float(co) <= 0:
                        continue
                    new_pos.append({
                        "ticker": tk,
                        "shares": float(sh),
                        "avg_cost": float(co),
                    })
                except Exception:
                    continue
            st.session_state["active_positions"] = new_pos[:MAX_ACTIVE_STOCKS]
            st.success("Saved " + str(len(st.session_state["active_positions"])) + " positions.")
            st.rerun()

        st.markdown(DIVIDER, unsafe_allow_html=True)
        st.subheader("CSV Import (first setup or full re-sync)")
        st.caption("Use this for the first load or an occasional broker re-sync. For daily tweaks, use the table above.")
        up = st.file_uploader("Upload broker CSV", type=["csv"], key="csv_up")
        if up is not None:
            parsed, err = _parse_csv(up)
            if err:
                st.error(err)
            else:
                st.markdown("**Preview**")
                st.dataframe(pd.DataFrame(parsed), use_container_width=True, hide_index=True)
                csv_mode = st.radio(
                    "Import mode",
                    ["Merge / update by ticker (keep the rest)", "Replace my whole portfolio"],
                    horizontal=True,
                    key="csv_mode")
                with st.form("csv_confirm"):
                    go = st.form_submit_button("Apply import", type="primary")
                    if go:
                        if csv_mode.startswith("Replace"):
                            st.session_state["active_positions"] = parsed[:MAX_ACTIVE_STOCKS]
                        else:
                            by_tk = {p["ticker"]: p for p in st.session_state["active_positions"]}
                            for r in parsed:
                                by_tk[r["ticker"]] = r
                            merged = list(by_tk.values())[:MAX_ACTIVE_STOCKS]
                            st.session_state["active_positions"] = merged
                        st.success("Imported. Review the cockpit and adjust costs if needed.")
                        st.rerun()

        st.markdown(DIVIDER, unsafe_allow_html=True)
        st.subheader("🔒 How your data is saved (private by design)")
        st.info(
            "Nothing is stored on a server. Your portfolio lives with you, "
            "in three free ways: (1) export a text code and paste it back later, "
            "(2) download a save-file to your own device, or (3) press "
            "'Save to this link' and bookmark the page. When the app naps and "
            "wakes up, any of these restores everything. Later, this same save "
            "layer can point at your own private Node or a cloud database.")
        blob = _current_blob()
        enc = _encode(blob)

        e1, e2 = st.columns(2)
        with e1:
            st.markdown("**Export / Import text code**")
            st.code(enc, language="text")
            st.download_button(
                "Download save-file (.json)",
                data=json.dumps(blob, indent=2),
                file_name="quantvantage-portfolio.json",
                mime="application/json",
                key="dl_json",
            )
            if st.button("Save to this link (then bookmark the page)", key="save_link", type="primary"):
                st.query_params["p"] = enc
                st.success("Saved into the page address. Bookmark or copy the address bar now.")
                st.rerun()
        with e2:
            st.markdown("**Restore from text code**")
            pasted = st.text_area("Paste a saved code here", height=120, key="paste_blob")
            if st.button("Import code", key="import_code"):
                try:
                    _apply_blob(_decode(pasted))
                    st.query_params["p"] = pasted.strip()
                    st.success("Restored from code.")
                    st.rerun()
                except Exception:
                    st.error("That code could not be read. Check it is complete.")
            st.markdown("**Restore from save-file**")
            up2 = st.file_uploader("Load a .json save-file", type=["json"], key="json_up")
            if up2 is not None:
                try:
                    _apply_blob(json.loads(up2.read().decode("utf-8")))
                    st.success("Restored from file.")
                    st.rerun()
                except Exception:
                    st.error("Could not read that file.")

        st.markdown(DIVIDER, unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        with d1:
            if st.button("Reset engine trims (after a manual re-sync)", key="reset_trims"):
                st.session_state["trimmed"] = {}
                st.session_state["settled"] = {}
                st.session_state["cash_adjust"] = 0.0
                st.success("Engine deltas reset. Your manual snapshot is now the source of truth.")
                st.rerun()
        with d2:
            if st.button("Clear all local data", key="clear_all"):
                for k in ["active_positions", "watchlist", "trimmed", "settled", "cash_adjust"]:
                    st.session_state[k] = ([] if k in ("active_positions", "watchlist") else ({} if k in ("trimmed", "settled") else 0.0))
                st.session_state["etf_value"] = 50000.0
                st.session_state["cash_value"] = 25000.0
                st.query_params.clear()
                st.success("Cleared.")
                st.rerun()

    # ================= FOOTER =================
    st.markdown(DIVIDER, unsafe_allow_html=True)
    st.caption(
        "⚠️ Informational only. Past performance does not guarantee future "
        "results. Sentiment tags are keyword estimates. All trades are at "
        "the user's own risk. Software only - no custody of funds.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
