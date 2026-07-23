"""
============================================================
S&P 500 Core Matrix - Portfolio Automation Dashboard
Version:  2.2.0  |  Date: 22 July 2026
Framework: Streamlit 1.35+  |  Python 3.11+
Tracks 38 designated assets (37 equities + SIVR) against a
rolling 52-week high, flags DCAX2 deployment triggers and
structured milestone take-profit levels, and enforces a
maximum of 10 active single-stock positions.
============================================================
"""

import streamlit as st
import yfinance as yf
import pandas as pd

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

# Display ticker -> Yahoo Finance lookup symbol.
# SK Hynix trades on the Korea Exchange and requires the .KS suffix.
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
# CACHED DATA FETCH (1-year daily history for all symbols)
# ============================================================

@st.cache_data(ttl=3600, show_spinner="Fetching market data from Yahoo Finance...")
def fetch_market_data():
    """
    Download 1-year daily price history for the full universe plus SPY.
    Returns:
        history:         dict of symbol -> DataFrame
        current_prices:  Series of latest close prices
        high_52w:        Series of 52-week highs (daily High column)
    """
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
            df = df.dropna(how="all")          # keep partially valid sessions
            if df.empty or "Close" not in df.columns:
                continue
            history[sym] = df
            current_prices[sym] = float(df["Close"].iloc[-1])
            high_52w[sym] = float(df["High"].max())
        except (KeyError, TypeError):
            continue                            # symbol unavailable; skip cleanly

    return history, pd.Series(current_prices), pd.Series(high_52w)


def read_secret(key):
    """Safely retrieve a credential from st.secrets without raising."""
    try:
        return st.secrets[key]
    except Exception:
        return None

# ============================================================
# POSITION CARD RENDERER
# ============================================================

def render_position_card(pos, idx, current_prices, high_52w, history):
    """Render a single cockpit card with DCAX2 and milestone logic."""
    display = pos["ticker"]
    sym = TICKER_MAP[display]
    cur = current_prices.get(sym)
    high = high_52w.get(sym)

    st.markdown(f"#### {display}")

    if cur is None or high is None:
        st.error("Market data unavailable for this symbol.")
    else:
        st.metric("Live Price", f"${cur:,.2f}")
        drawdown = (cur - high) / high

        st.caption(f"52W High: ${high:,.2f} · Deviation: {drawdown:.1%}")
        st.progress(min(abs(drawdown) / 0.40, 1.0))

        # --- DCAX2 trigger evaluation ---
        if drawdown <= DCAX2_THRESHOLD:
            st.error("⚠️ DCAX2 TRIGGERED: DEPLOY 3x BUY SIZE")
        else:
            st.info("Baseline DCA (1x)")

        # --- Milestone trim evaluation (highest reached level wins) ---
        cost = pos["avg_cost"]
        if cost > 0:
            multiple = cur / cost
            triggered = [lvl for lvl in MILESTONE_LEVELS if multiple >= lvl]
            if triggered:
                level = max(triggered)
                gain_pct = (level - 1) * 100
                st.warning(f"💰 MILESTONE TRIM TRIGGERED: +{gain_pct:.0f}% — LOCK IN PROFITS")

        st.caption(f"Position Value: ${pos['shares'] * cur:,.2f}")

        # --- 30-day trend sparkline (native Streamlit, no extra dependency) ---
        if sym in history:
            st.line_chart(history[sym]["Close"].tail(30), height=80)

    if st.button("❌ Remove", key=f"rem_{idx}"):
        st.session_state.active_positions.pop(idx)
        st.rerun()

# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    # Session state initialization
    if "active_positions" not in st.session_state:
        st.session_state.active_positions = []

    history, current_prices, high_52w = fetch_market_data()

    # ================= SIDEBAR =================
    with st.sidebar:
        st.title("🏦 Financial Housekeeping")
        st.markdown("---")

        st.subheader("Pre-Investment Gate")
        emergency_ok = st.checkbox("✔ 6–12 month emergency cash buffer secured", value=True)
        debt_ok = st.checkbox("✔ 0% high-interest non-mortgage debt", value=True)
        tax_ok = st.checkbox("✔ Tax-shield vehicles maximised (401k, IRA, HSA)", value=True)
        if emergency_ok and debt_ok and tax_ok:
            st.success("Gate cleared: deployment permitted")
        else:
            st.error("Gate closed: deploy only after all checks pass")

        st.markdown("---")
        st.subheader("Monthly Capital Split")
        etf_pct = st.slider(
            "S&P 500 ETF Allocation (%)",
            min_value=0, max_value=100, value=50, step=5,
            help="Percentage of each monthly contribution routed to SPY. "
                 "Remainder flows to the single-stock dry powder pool.",
        )
        col_a, col_b = st.columns(2)
        col_a.metric("SPY Allocation", f"{etf_pct}%")
        col_b.metric("Dry Powder Pool", f"{100 - etf_pct}%")

        st.markdown("---")
        st.subheader("Portfolio Values ($)")
        etf_value = st.number_input("Current SPY/ETF Value", min_value=0.0, value=50000.0, step=1000.0)
        cash_value = st.number_input("Current Dry Powder Cash Reserve", min_value=0.0, value=25000.0, step=1000.0)

        st.markdown("---")
        st.subheader("🔐 Broker Integration")
        st.success("IBKR token sealed in vault") if read_secret("IBKR_TOKEN") else \
            st.info("Add IBKR_TOKEN to secrets for Interactive Brokers linking")
        st.success("Trading 212 token sealed in vault") if read_secret("T212_TOKEN") else \
            st.info("Add T212_TOKEN to secrets for Trading 212 linking")

        st.markdown("---")
        st.caption("All data sourced from Yahoo Finance. Not financial advice.")

    # ================= MAIN DASHBOARD =================
    st.title("📈 S&P 500 Core Matrix — Automated Portfolio Tracker")

    if current_prices.empty:
        st.error("Market data fetch failed. Yahoo Finance may be rate-limiting. "
                 "Please retry in a few minutes.")
        return

    # Data freshness + manual refresh control
    header_col, refresh_col = st.columns([5, 1])
    with header_col:
        if SPY_TICKER in history:
            last_session = history[SPY_TICKER].index[-1].strftime("%d %B %Y")
            st.caption(f"Data through last close: **{last_session}** · Cache TTL: 60 minutes")
    with refresh_col:
        if st.button("🔄 Refresh Data", use_container_width=True):
            fetch_market_data.clear()
            st.rerun()

    # ----- TOP ROW: Portfolio summary -----
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total ETF Holdings", f"${etf_value:,.2f}")
    col2.metric("Dry Powder Reserve", f"${cash_value:,.2f}")

    total_stock_val = sum(
        pos["shares"] * current_prices[TICKER_MAP[pos["ticker"]]]
        for pos in st.session_state.active_positions
        if TICKER_MAP[pos["ticker"]] in current_prices
    )
    col3.metric("Active Stock Value", f"${total_stock_val:,.2f}")
    col4.metric("Total Portfolio", f"${etf_value + cash_value + total_stock_val:,.2f}")

    st.markdown("---")

    # ----- ACTIVE 10-STOCK COCKPIT -----
    st.subheader(f"🎯 Active Single-Stock Workspace ({len(st.session_state.active_positions)} / {MAX_ACTIVE_STOCKS} slots)")

    if len(st.session_state.active_positions) < MAX_ACTIVE_STOCKS:
        with st.expander("➕ Add a new position", expanded=False):
            with st.form("add_position_form", clear_on_submit=True):
                held = [p["ticker"] for p in st.session_state.active_positions]
                new_ticker = st.selectbox(
                    "Select ticker",
                    options=[t for t in TICKER_MAP if t not in held],
                    index=None,
                    placeholder="Choose a stock...",
                )
                avg_cost = st.number_input("Average Cost per Share ($)", min_value=0.01, value=100.0, step=1.0)
                shares = st.number_input("Number of Shares", min_value=0.0, value=1.0, step=1.0)
                if st.form_submit_button("Add to Cockpit") and new_ticker:
                    st.session_state.active_positions.append({
                        "ticker": new_ticker,
                        "avg_cost": avg_cost,
                        "shares": shares,
                    })
                    st.rerun()
    else:
        st.warning("Maximum 10 active positions reached. Remove one before adding another.")

    if st.session_state.active_positions:
        # Re-flow cards into rows of five for readability
        positions = st.session_state.active_positions
        for row_start in range(0, len(positions), 5):
            row = positions[row_start:row_start + 5]
            cols = st.columns(len(row))
            for col, pos in zip(cols, row):
                with col:
                    render_position_card(pos, row_start + row.index(pos),
                                         current_prices, high_52w, history)
    else:
        st.info("No active positions yet. Use the form above to add up to 10 stocks.")

    st.markdown("---")

    # ----- GLOBAL MATRIX WATCHLIST -----
    st.subheader("🌍 Global Matrix Watchlist (37 equities + SIVR)")
    with st.expander("Click to expand full watchlist", expanded=False):
        rows = []
        for display, sym in TICKER_MAP.items():
            cur = current_prices.get(sym)
            high = high_52w.get(sym)
            if cur is None or high is None:
                rows.append({"Ticker": display, "Price": None, "52W High": None,
                             "Deviation %": None, "DCA Status": "DATA UNAVAILABLE"})
                continue
            dev_pct = (cur - high) / high * 100
            rows.append({
                "Ticker": display,
                "Price": cur,
                "52W High": high,
                "Deviation %": dev_pct,
                "DCA Status": "⚠️ DCAX2" if dev_pct <= DCAX2_THRESHOLD * 100 else "Baseline",
            })

        df_watchlist = (
            pd.DataFrame(rows)
            .sort_values("Deviation %", ascending=True, na_position="last")
            .reset_index(drop=True)
        )
        st.dataframe(
            df_watchlist,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Price": st.column_config.NumberColumn("Current Price", format="$%.2f"),
                "52W High": st.column_config.NumberColumn("52-Week High", format="$%.2f"),
                "Deviation %": st.column_config.NumberColumn("Deviation from High", format="%.1f%%"),
                "DCA Status": st.column_config.TextColumn("Buy Signal"),
            },
        )
        st.caption("Table sorted by deviation from 52-week high (largest discounts first).")

    st.markdown("---")
    st.caption("⚠️ This tool is for informational purposes only. "
               "Past performance does not guarantee future results. "
               "All trades are executed at the user's own risk.")

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()