"""
S&P 500 Core Matrix - Portfolio Automation Dashboard
Version 2.3.1 - copy-safe premium build - 23 July 2026
Streamlit 1.35+ and Python 3.11+
Tracks 38 assets (37 equities + SIVR) vs a rolling 52-week
high, flags DCAX2 triggers and milestone take-profit levels,
caps active positions at 10, and renders an institutional
dark theme. The HTML layer uses only short string pieces so
the source is robust to copy and paste line wrapping.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import math

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

SPY_TICKER = "SPY"
MAX_ACTIVE_STOCKS = 10
MILESTONE_LEVELS = [1.5, 2.0, 2.5, 3.0]
DCAX2_THRESHOLD = -0.20

# Dollar sign as an HTML entity so Streamlit never reads
# currency figures as LaTeX math.
DS = "&#" + "36;"

DIVIDER = (
    '<div style="height:1px;'
    'background:#1e293b;margin:22px 0"></div>'
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
# PREMIUM THEME CSS (multi-line string, safe to wrap)
# ============================================================

PREMIUM_CSS = '''
<style>
.stApp { background:#020617; }
section[data-testid="stSidebar"] { background:#0b1220; }
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label { color:#cbd5e1; }
.stApp h1, .stApp h2, .stApp h3 {
  color:#f8fafc; letter-spacing:-0.01em;
}
.stApp p, .stApp .stMarkdown { color:#cbd5e1; }
[data-testid="stMetric"] {
  background:#0f172a; border:1px solid #1e293b;
  border-radius:14px; padding:12px 14px;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-family:ui-monospace,Menlo,monospace; color:#f8fafc;
}
[data-testid="stMetric"] [data-testid="stMetricLabel"] {
  color:#94a3b8;
}
.stButton>button {
  background:#0f172a; color:#e2e8f0;
  border:1px solid #334155; border-radius:10px;
}
.stButton>button:hover { border-color:#10b981; color:#fff; }
details {
  background:#0f172a; border:1px solid #1e293b;
  border-radius:12px;
}
.qvn-kpi-grid {
  display:grid; grid-template-columns:repeat(4,1fr);
  gap:14px; margin:6px 0 8px;
}
@media(max-width:900px){
  .qvn-kpi-grid { grid-template-columns:repeat(2,1fr); }
}
.qvn-kpi {
  background:#0f172a; border:1px solid #1e293b;
  border-radius:16px; padding:16px 18px;
  box-shadow:0 18px 48px -28px rgba(0,0,0,.7);
}
.qvn-kpi-label {
  font-size:11px; text-transform:uppercase;
  letter-spacing:.12em; color:#64748b;
}
.qvn-kpi-val {
  font-family:ui-monospace,Menlo,monospace;
  font-size:24px; font-weight:700; color:#f8fafc;
  margin-top:6px;
}
.qvn-kpi-val.pos { color:#34d399; }
.qvn-kpi-val.neg { color:#fb7185; }
.qvn-kpi-val.amb { color:#fbbf24; }
.qvn-kpi-sub {
  font-size:11px; color:#64748b; margin-top:4px;
  font-family:ui-monospace,monospace;
}
.qvn-card {
  background:#0f172a; border:1px solid #1e293b;
  border-radius:16px; padding:16px;
  box-shadow:0 18px 48px -28px rgba(0,0,0,.7);
  min-height:340px; display:flex;
  flex-direction:column; gap:8px;
}
.qvn-card-head {
  display:flex; align-items:center;
  justify-content:space-between;
}
.qvn-ticker {
  font-family:ui-monospace,monospace;
  font-size:18px; font-weight:700; color:#fff;
}
.qvn-chip {
  font-family:ui-monospace,monospace; font-size:9px;
  letter-spacing:.1em; text-transform:uppercase;
  background:#1e293b; color:#94a3b8;
  padding:2px 7px; border-radius:6px;
}
.qvn-price {
  font-family:ui-monospace,monospace;
  font-size:22px; font-weight:700; color:#fff;
}
.qvn-sub { font-size:11px; color:#64748b; }
.qvn-pos { color:#34d399; }
.qvn-neg { color:#fb7185; }
.qvn-meter {
  height:6px; background:#1e293b;
  border-radius:99px; overflow:hidden;
}
.qvn-meter-fill {
  height:100%; background:#475569;
  border-radius:99px; transition:width .5s;
}
.qvn-meter-amber { background:#f59e0b; }
.qvn-row {
  display:flex; justify-content:space-between;
  font-size:12px; color:#94a3b8;
}
.qvn-row b {
  font-family:ui-monospace,monospace; color:#e2e8f0;
}
.qvn-banner-trim {
  margin-top:auto; background:rgba(16,185,129,.12);
  border:1px solid rgba(16,185,129,.4);
  border-radius:10px; padding:8px 10px;
  font-size:11px; font-weight:700; color:#6ee7b7;
  text-align:center;
}
.qvn-badge-dcax2 {
  margin-top:auto; background:#f59e0b;
  border-radius:10px; padding:10px;
  font-size:11px; font-weight:800;
  letter-spacing:.02em; color:#0b1220;
  text-align:center; animation:qvnflash 1.1s ease-in-out infinite;
}
.qvn-nominal {
  margin-top:auto; background:#0b1220;
  border:1px solid #1e293b; border-radius:10px;
  padding:8px; font-size:10px; letter-spacing:.12em;
  text-transform:uppercase; color:#64748b; text-align:center;
}
@keyframes qvnflash {
  0%,100% { opacity:1; box-shadow:0 0 22px -4px rgba(245,158,11,.8); }
  50% { opacity:.55; box-shadow:0 0 8px -4px rgba(245,158,11,.3); }
}
.qvn-balance { display:flex; flex-direction:column; gap:10px; }
.qvn-legend {
  display:flex; align-items:center;
  justify-content:space-between;
  border:1px solid; border-radius:12px; padding:12px 14px;
}
.qvn-leg-name { font-size:13px; font-weight:600; color:#fff; }
.qvn-leg-desc { font-size:11px; color:#64748b; }
.qvn-leg-val {
  font-family:ui-monospace,monospace;
  font-size:13px; font-weight:700; color:#fff;
}
.qvn-leg-pct { font-family:ui-monospace,monospace; font-size:11px; }
.qvn-bar {
  display:flex; height:10px; border-radius:99px;
  overflow:hidden; background:#1e293b;
}
.qvn-ms-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.qvn-ms {
  background:#0b1220; border:1px solid #1e293b;
  border-radius:12px; padding:12px; text-align:center;
}
.qvn-ms.lit {
  background:rgba(16,185,129,.1);
  border-color:rgba(16,185,129,.45);
  box-shadow:0 0 30px -10px rgba(16,185,129,.5);
}
.qvn-ms-l {
  font-family:ui-monospace,monospace;
  font-size:11px; font-weight:700; color:#64748b;
}
.qvn-ms.lit .qvn-ms-l { color:#6ee7b7; }
.qvn-ms-v {
  font-family:ui-monospace,monospace;
  font-size:15px; font-weight:700; color:#cbd5e1; margin-top:2px;
}
.qvn-ms.lit .qvn-ms-v { color:#fff; }
.qvn-ms-c { font-size:10px; color:#475569; margin-top:2px; }
.qvn-ms.lit .qvn-ms-c { color:#34d399; }
.qvn-table-wrap {
  max-height:520px; overflow:auto;
  border:1px solid #1e293b; border-radius:14px;
}
table.qvn-table { width:100%; border-collapse:collapse; font-size:13px; }
table.qvn-table thead th {
  position:sticky; top:0; background:#0b1220;
  text-align:left; padding:12px 16px; font-size:10px;
  letter-spacing:.1em; text-transform:uppercase;
  color:#64748b; border-bottom:1px solid #1e293b;
}
table.qvn-table td {
  padding:11px 16px; border-bottom:1px solid rgba(30,41,59,.6);
  color:#cbd5e1; font-family:ui-monospace,monospace;
}
table.qvn-table tr.qvn-trig { background:rgba(245,158,11,.06); }
.qvn-td-tk { color:#fff; font-weight:700; }
.qvn-sig-dcax {
  background:rgba(245,158,11,.18); color:#fcd34d;
  padding:2px 8px; border-radius:6px; font-size:10px; font-weight:700;
}
.qvn-sig-base {
  background:#1e293b; color:#94a3b8;
  padding:2px 8px; border-radius:6px; font-size:10px; font-weight:700;
}
</style>
'''


def inject_premium_theme():
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# ============================================================
# NUMBER FORMATTERS (short, robust, no f-strings)
# ============================================================

def _f2(x):
    return "{:,.2f}".format(x)

def _f0(x):
    return "{:,.0f}".format(x)

def _p1(x):
    return "{:.1f}".format(x)

def _p0(x):
    return "{:.0f}".format(x)

def _p2(x):
    return "{:.2f}".format(x)

def _pct1(x):
    return "{:.1f}%".format(x)

def _pcti(x):
    return "{:.1%}".format(x)

def _psgn(x):
    return "{:+.1f}%".format(x)

# ============================================================
# CACHED DATA FETCH
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
    history = {}
    current_prices = {}
    high_52w = {}
    if data is None or data.empty:
        empty = pd.Series(dtype=float)
        return history, empty, empty
    for sym in symbols:
        try:
            if len(symbols) > 1:
                df = data[sym].copy()
            else:
                df = data.copy()
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
# PREMIUM HTML BUILDERS (short pieces only)
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
    vb = "0 0 " + _p0(W) + " " + _p0(H)
    return (
        '<svg viewBox="' + vb + '" '
        + 'preserveAspectRatio="none" '
        + 'style="width:100%;height:34px">'
        + '<polyline points="' + poly + '" '
        + 'fill="none" stroke="' + color + '" '
        + 'stroke-width="2" stroke-linecap="round" '
        + 'stroke-linejoin="round"/></svg>'
    )


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
        + DS + _f0(total) + '</div></div>'
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
    spx_p = _pct1(spx / total * 100)
    act_v = DS + _f2(active)
    act_p = _pct1(active / total * 100)
    dry_v = DS + _f2(dry)
    dry_p = _pct1(max(dry, 0) / total * 100)
    rows = [
        _leg("#10b981", "S&amp;P 500 Index Core",
             "Baseline anchor", spx_v, spx_p),
        _leg("#0ea5e9", "Active Stock Workspace",
             "DCAX2 operational slots", act_v, act_p),
        _leg("#f59e0b", "Dry Powder Buffer",
             "Cash deployment reserve", dry_v, dry_p),
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
    for pos in positions:
        sym = TICKER_MAP[pos["ticker"]]
        cur = prices.get(sym)
        cost = pos["avg_cost"]
        if cur and cost > 0:
            mult = cur / cost
            for m in MILESTONE_LEVELS:
                if mult >= m:
                    counts[m] += 1
    cells = ""
    for i, m in enumerate(MILESTONE_LEVELS):
        lit = "lit" if counts[m] > 0 else ""
        gp = int((m - 1) * 100)
        cells += (
            '<div class="qvn-ms ' + lit + '">'
            + '<div class="qvn-ms-l">M' + str(i + 1) + '</div>'
            + '<div class="qvn-ms-v">+' + str(gp) + '%</div>'
            + '<div class="qvn-ms-c">' + str(counts[m]) + ' hit</div></div>'
        )
    return '<div class="qvn-ms-grid">' + cells + '</div>'


def cockpit_card_html(pos, cur, high, history):
    sym = TICKER_MAP[pos["ticker"]]
    cost = pos["avg_cost"]
    shares = pos["shares"]
    drawdown = (cur - high) / high if high else 0.0
    pnl_pct = (cur - cost) / cost * 100 if cost else 0.0
    positive = pnl_pct >= 0
    dcax = drawdown <= DCAX2_THRESHOLD
    dd_sev = min(abs(drawdown) / 0.40, 1.0) * 100
    banner = ""
    if cost > 0:
        mult = cur / cost
        trig = [l for l in MILESTONE_LEVELS if mult >= l]
        if trig:
            lvl = max(trig)
            gp = int((lvl - 1) * 100)
            banner = (
                '<div class="qvn-banner-trim">'
                + '&#128176; MILESTONE TRIM +' + str(gp)
                + '% &mdash; LOCK IN PROFITS</div>'
            )
    spark = ""
    if sym in history:
        spark = sparkline_svg(history[sym]["Close"], positive)
    if dcax:
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
    dev_cls = "qvn-neg" if drawdown < 0 else "qvn-pos"
    gain_cls = "qvn-pos" if positive else "qvn-neg"
    chip = "DCAX2" if dcax else "DCA"
    posval = shares * cur
    fill_cls = "qvn-meter-amber" if dcax else ""
    meter = (
        '<div class="qvn-meter">'
        + '<div class="qvn-meter-fill ' + fill_cls
        + '" style="width:' + _p0(dd_sev) + '%"></div></div>'
    )
    head = (
        '<div class="qvn-card">'
        + '<div class="qvn-card-head">'
        + '<span class="qvn-ticker">' + pos["ticker"] + '</span>'
        + '<span class="qvn-chip">' + chip + '</span></div>'
        + '<div class="qvn-price">' + DS + _f2(cur) + '</div>'
        + '<div class="qvn-sub">52W High ' + DS + _f2(high)
        + ' &middot; Dev <span class="' + dev_cls + '">'
        + _pcti(drawdown) + '</span></div>'
    )
    rows = (
        '<div class="qvn-row"><span>Shares</span><b>'
        + _f0(shares) + '</b></div>'
        + '<div class="qvn-row"><span>Avg Cost</span><b>'
        + DS + _f2(cost) + '</b></div>'
        + '<div class="qvn-row"><span>Value</span><b>'
        + DS + _f2(posval) + '</b></div>'
        + '<div class="qvn-row"><span>Gain</span>'
        + '<b class="' + gain_cls + '">' + _psgn(pnl_pct) + '</b></div>'
    )
    return head + meter + rows + spark + banner + alert + '</div>'


def wl_row(r):
    dev = r["dev"]
    cls = "qvn-trig" if r["dcax"] else ""
    dev_cls = "qvn-neg" if (dev is not None and dev < 0) else "qvn-pos"
    dev_txt = _p1(dev) + "%" if dev is not None else "N/A"
    price_txt = DS + _f2(r["cur"]) if r["cur"] is not None else "N/A"
    high_txt = DS + _f2(r["high"]) if r["high"] is not None else "N/A"
    if r["dcax"]:
        sig = '<span class="qvn-sig-dcax">&#9888; DCAX2</span>'
    else:
        sig = '<span class="qvn-sig-base">Baseline</span>'
    return (
        '<tr class="' + cls + '">'
        + '<td class="qvn-td-tk">' + r["ticker"] + '</td>'
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
        '<thead><tr><th>Ticker</th>'
        + '<th>Live Price</th><th>52-Week High</th>'
        + '<th>Deviation</th><th>Signal</th></tr></thead>'
    )
    body = "<tbody>" + "".join(wl_row(r) for r in rows) + "</tbody>"
    return (
        '<div class="qvn-table-wrap">'
        + '<table class="qvn-table">' + head + body + '</table></div>'
    )

# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    inject_premium_theme()

    if "active_positions" not in st.session_state:
        st.session_state.active_positions = []
    positions = st.session_state.active_positions

    history, current_prices, high_52w = fetch_market_data()

    # ---------- SIDEBAR ----------
    with st.sidebar:
        st.title("🏦 Financial Housekeeping")
        st.markdown("---")
        st.subheader("Pre-Investment Gate")
        emergency_ok = st.checkbox(
            "✔ 6-12 month emergency cash buffer secured", value=True)
        debt_ok = st.checkbox(
            "✔ 0% high-interest non-mortgage debt", value=True)
        tax_ok = st.checkbox(
            "✔ Tax-shield vehicles maximised (401k, IRA, HSA)", value=True)
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
        col_a, col_b = st.columns(2)
        col_a.metric("SPY Allocation", str(etf_pct) + "%")
        col_b.metric("Dry Powder Pool", str(100 - etf_pct) + "%")
        st.markdown("---")
        st.subheader("Portfolio Values")
        etf_value = st.number_input(
            "Current SPY/ETF Value",
            min_value=0.0, value=50000.0, step=1000.0)
        cash_value = st.number_input(
            "Current Dry Powder Cash Reserve",
            min_value=0.0, value=25000.0, step=1000.0)
        st.markdown("---")
        st.subheader("🔐 Broker Integration")
        if read_secret("IBKR_TOKEN"):
            st.success("IBKR token sealed in vault")
        else:
            st.info("Add IBKR_TOKEN to secrets for IBKR linking")
        if read_secret("T212_TOKEN"):
            st.success("Trading 212 token sealed in vault")
        else:
            st.info("Add T212_TOKEN to secrets for Trading 212 linking")
        st.markdown("---")
        st.caption("Data from Yahoo Finance. Not financial advice.")

    # ---------- MAIN ----------
    st.title("📈 S&P 500 Core Matrix — Automated Portfolio Tracker")

    if current_prices.empty:
        st.error(
            "Market data fetch failed. Yahoo Finance may be "
            "rate-limiting. Please retry in a few minutes.")
        return

    header_col, refresh_col = st.columns([5, 1])
    with header_col:
        if SPY_TICKER in history:
            last = history[SPY_TICKER].index[-1].strftime("%d %B %Y")
            st.caption("Data through last close: **" + last + "** · Cache TTL: 60 minutes")
    with refresh_col:
        if st.button("🔄 Refresh Data", use_container_width=True):
            fetch_market_data.clear()
            st.rerun()

    # ----- KPI TILES -----
    total_stock_val = 0.0
    for pos in positions:
        sym = TICKER_MAP[pos["ticker"]]
        if sym in current_prices and current_prices[sym] is not None:
            total_stock_val += pos["shares"] * current_prices[sym]
    total_portfolio = etf_value + cash_value + total_stock_val

    st.markdown(
        kpi_grid_html([
            ("Total ETF Holdings", DS + _f2(etf_value),
             "S&P 500 baseline core", ""),
            ("Dry Powder Reserve", DS + _f2(cash_value),
             "Cash awaiting deployment", "amb"),
            ("Active Stock Value", DS + _f2(total_stock_val),
             str(len(positions)) + " operational slots", ""),
            ("Total Portfolio", DS + _f2(total_portfolio),
             "Net liquidation value", "pos"),
        ]),
        unsafe_allow_html=True,
    )
    st.markdown(DIVIDER, unsafe_allow_html=True)

    # ----- CORE BALANCE TRACKER -----
    st.subheader("🧭 Core Balance Tracker")
    bc1, bc2 = st.columns([2, 3])
    with bc1:
        st.markdown(
            donut_html(etf_value, total_stock_val, cash_value),
            unsafe_allow_html=True,
        )
    with bc2:
        st.markdown(
            legend_html(etf_value, total_stock_val, cash_value)
            + bar_html(etf_value, total_stock_val, cash_value),
            unsafe_allow_html=True,
        )
    st.markdown(DIVIDER, unsafe_allow_html=True)

    # ----- CAPITAL RECYCLING ENGINE -----
    st.subheader("♻️ Capital Recycling Engine")
    st.markdown(
        milestone_ladder_html(positions, current_prices),
        unsafe_allow_html=True,
    )
    st.caption(
        "When a holding crosses +50 / +100 / +150 / +200%, "
        "its cockpit card shows the emerald TRIM banner.")
    st.markdown(DIVIDER, unsafe_allow_html=True)

    # ----- 10-STOCK COCKPIT -----
    st.subheader(
        "🎯 Active Single-Stock Workspace ("
        + str(len(positions)) + " / "
        + str(MAX_ACTIVE_STOCKS) + " slots)")

    if len(positions) < MAX_ACTIVE_STOCKS:
        with st.expander("➕ Add a new position", expanded=False):
            with st.form("add_position_form", clear_on_submit=True):
                held = [p["ticker"] for p in positions]
                new_ticker = st.selectbox(
                    "Select ticker",
                    options=[t for t in TICKER_MAP if t not in held],
                    index=None,
                    placeholder="Choose a stock...",
                )
                avg_cost = st.number_input(
                    "Average Cost per Share",
                    min_value=0.01, value=100.0, step=1.0)
                shares = st.number_input(
                    "Number of Shares",
                    min_value=0.0, value=1.0, step=1.0)
                if st.form_submit_button("Add to Cockpit") and new_ticker:
                    st.session_state.active_positions.append({
                        "ticker": new_ticker,
                        "avg_cost": avg_cost,
                        "shares": shares,
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
                sym = TICKER_MAP[pos["ticker"]]
                cur = current_prices.get(sym)
                high = high_52w.get(sym)
                with cols[i]:
                    if cur is None or high is None:
                        st.markdown(
                            '<div class="qvn-card">'
                            + '<div class="qvn-ticker">' + pos["ticker"] + '</div>'
                            + '<div class="qvn-sub">Market data unavailable</div></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            cockpit_card_html(pos, cur, high, history),
                            unsafe_allow_html=True,
                        )
                    if st.button(
                        "❌ Remove " + pos["ticker"],
                        key="rem_" + str(idx),
                        use_container_width=True,
                    ):
                        st.session_state.active_positions.pop(idx)
                        st.rerun()
    else:
        st.info("No active positions yet. Use the form above to add up to 10 stocks.")
    st.markdown(DIVIDER, unsafe_allow_html=True)

    # ----- GLOBAL MATRIX WATCHLIST -----
    st.subheader("🌍 Global Matrix Watchlist (37 equities + SIVR)")
    fc1, fc2 = st.columns([3, 2])
    with fc1:
        search = st.text_input("Search ticker", "")
    with fc2:
        sigf = st.selectbox(
            "Signal filter",
            ["All signals", "DCAX2 triggered only", "Baseline only"],
        )

    rows = []
    for display, sym in TICKER_MAP.items():
        cur = current_prices.get(sym)
        high = high_52w.get(sym)
        if cur is None or high is None:
            dev = None
            dcax = False
        else:
            dev = (cur - high) / high * 100
            dcax = dev <= DCAX2_THRESHOLD * 100
        rows.append({
            "ticker": display,
            "cur": cur,
            "high": high,
            "dev": dev,
            "dcax": dcax,
        })

    s = search.strip().upper()
    if s:
        rows = [r for r in rows if s in r["ticker"]]
    if sigf == "DCAX2 triggered only":
        rows = [r for r in rows if r["dcax"]]
    elif sigf == "Baseline only":
        rows = [r for r in rows if (r["dev"] is not None and not r["dcax"])]
    rows.sort(key=lambda r: (r["dev"] if r["dev"] is not None else 9999))

    st.markdown(watchlist_html(rows), unsafe_allow_html=True)
    st.caption(
        "Sorted by deviation from 52-week high — deepest discounts first. "
        "Amber rows are your DCAX2 buy candidates.")
    st.markdown(DIVIDER, unsafe_allow_html=True)
    st.caption(
        "⚠️ This tool is for informational purposes only. "
        "Past performance does not guarantee future results. "
        "All trades are executed at the user's own risk.")

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
