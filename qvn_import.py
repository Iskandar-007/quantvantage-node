"""
QuantVantage Node - smart CSV importer (v3.1.0)
Reads three different broker file shapes without ever crashing:
  1) Interactive Brokers Activity Statement (sectioned document)
  2) A flat holdings snapshot (one row per current position)
  3) A flat transaction history (reconstructed into an ESTIMATE)
All parsing uses Python's csv module, which tolerates the
variable column counts that broke the old generic reader.
"""

import csv
import io
import streamlit as st
import pandas as pd

MAX_ACTIVE = 10
DS = "&#" + "36;"


def _f2(x):
    return "{:,.2f}".format(float(x))


# Broad-market index ETFs. If found in a holdings file we simply
# flag them so you can decide where they belong (we never move
# your numbers silently).
INDEX_ETF_TICKERS = set([
    "SPY", "VOO", "IVV", "SPLG", "SPXL", "SPXS",
    "QQQ", "QQQM", "QYLD", "TQQQ", "SQQQ",
    "VTI", "VUG", "VTV", "VIG", "VYM", "SCHD", "DIA",
    "VUSA", "CSPX", "SXR8", "VUAA", "VWRL", "IWDA",
])


# ------------------------------------------------------------
# Low level: read any CSV into a list of rows (list of fields)
# ------------------------------------------------------------

def _read_rows(file):
    raw = file.getvalue()
    try:
        text = raw.decode("utf-8-sig")
    except Exception:
        text = raw.decode("latin-1", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = []
    for r in reader:
        if r and not (len(r) == 1 and r[0].strip() == ""):
            rows.append(r)
    return rows


def _detect_format(rows):
    if not rows:
        return "empty"
    markers = set([
        "Statement", "Account Information", "Open Positions",
        "Net Asset Value", "Change in NAV", "Cash Report",
        "Financial Instrument Information",
    ])
    col0 = set()
    for r in rows[:400]:
        if r:
            col0.add(r[0].strip())
    if len(col0 & markers) >= 2:
        return "ibkr"
    header = [c.strip().lower() for c in rows[0]]
    if "action" in header:
        return "transactions"
    return "holdings"


# ------------------------------------------------------------
# Parser 1: IBKR Activity Statement  (exact holdings)
# ------------------------------------------------------------

def _parse_ibkr(rows):
    op_cols = None
    positions = []
    warnings = []
    for r in rows:
        if len(r) < 2:
            continue
        sec = r[0].strip()
        typ = r[1].strip()
        if sec == "Open Positions" and typ == "Header":
            op_cols = {}
            for i, name in enumerate(r):
                key = name.strip()
                if key:
                    op_cols[key] = i
        elif sec == "Open Positions" and typ == "Data" and op_cols is not None:
            def g(name):
                i = op_cols.get(name)
                if i is None or i >= len(r):
                    return ""
                return r[i].strip()
            if g("DataDiscriminator") != "Summary":
                continue
            if g("Asset Category") != "Stocks":
                continue
            sym = g("Symbol").upper()
            if not sym:
                continue
            try:
                qty = float(g("Quantity"))
            except Exception:
                continue
            if qty <= 0:
                continue
            cost = None
            try:
                cost = float(g("Cost Price"))
            except Exception:
                cost = None
            if cost is None or cost <= 0:
                try:
                    cost = float(g("Cost Basis")) / qty
                except Exception:
                    cost = 0.01
            positions.append({
                "ticker": sym,
                "shares": qty,
                "avg_cost": max(cost, 0.01),
            })
    idx_etfs = sorted(set(
        p["ticker"] for p in positions if p["ticker"] in INDEX_ETF_TICKERS
    ))
    if idx_etfs:
        warnings.append(
            "Index ETFs imported as positions: " + ", ".join(idx_etfs) +
            ". These are your broad-market baseline. If you would rather "
            "keep them out of the active cockpit, remove them here and add "
            "their value to the sidebar 'S&P 500 / ETF value' instead."
        )
    if not positions:
        return None, ["No stock positions found in the Open Positions section."]
    return positions, warnings


# ------------------------------------------------------------
# Parser 2: transaction history  (estimate only)
# ------------------------------------------------------------

def _parse_transactions(rows):
    header = [c.strip() for c in rows[0]]
    low = [h.lower() for h in header]

    def col(*names):
        for n in names:
            if n in low:
                return low.index(n)
        return None

    i_act = col("action")
    i_tk = col("ticker")
    i_sh = col("no. of shares", "shares", "quantity")
    i_pr = col("price / share", "price")
    i_cur = col("currency (price / share)", "currency")
    warnings = []
    if i_act is None or i_tk is None or i_sh is None:
        return None, [
            "This looks like a transaction history but the expected "
            "columns (Action / Ticker / shares) were not found."
        ]

    # ticker -> [net_qty, cost_sum, buy_qty, flags]
    net = {}
    for r in rows[1:]:
        if len(r) <= max(i_act, i_tk, i_sh):
            continue
        act = r[i_act].strip().lower()
        tk = r[i_tk].strip().upper()
        if not tk:
            continue
        try:
            s = float(r[i_sh])
        except Exception:
            continue
        if s == 0:
            continue
        p = 0.0
        if i_pr is not None and i_pr < len(r) and r[i_pr].strip() not in ("", "0"):
            try:
                p = float(r[i_pr])
            except Exception:
                p = 0.0
        cur = "USD"
        if i_cur is not None and i_cur < len(r):
            cur = r[i_cur].strip().upper() or "USD"
        rec = net.setdefault(tk, [0.0, 0.0, 0.0, set()])
        if cur and cur != "USD":
            rec[3].add("non-USD")
        if ("split" in act) or ("acquisition" in act) or ("adjustment" in act):
            rec[3].add("corporate-action")
            continue
        if "buy" in act:
            rec[0] += s
            if p > 0:
                rec[1] += s * p
                rec[2] += s
        elif "sell" in act:
            rec[0] -= s
        # dividends / interest / deposits / withdrawals are ignored

    positions = []
    flagged = []
    for tk, rec in net.items():
        nq = rec[0]
        if nq <= 1e-6:
            continue
        avg = (rec[1] / rec[2]) if rec[2] > 0 else 0.0
        positions.append({
            "ticker": tk,
            "shares": round(nq, 6),
            "avg_cost": max(avg, 0.01),
        })
        if rec[3]:
            flagged.append(tk + " (" + ", ".join(sorted(rec[3])) + ")")

    warnings.append(
        "This file is a TRANSACTION HISTORY, not a holdings snapshot. "
        "Holdings were reconstructed by netting buys and sells within the "
        "file's date range only. Positions opened before that range, or "
        "affected by splits / mergers, or bought in another currency, may "
        "be wrong or missing. Treat this as a rough draft and correct it "
        "in the editable table."
    )
    if flagged:
        warnings.append(
            "Double-check these (corporate action or non-USD trade): " +
            ", ".join(sorted(flagged)) + "."
        )
    if not positions:
        warnings.append("No current holdings could be reconstructed.")
        return None, warnings
    return positions, warnings


# ------------------------------------------------------------
# Parser 3: flat holdings snapshot  (exact)
# ------------------------------------------------------------

def _parse_holdings(rows):
    header = [c.strip() for c in rows[0]]
    low = [h.lower() for h in header]

    def col(*names):
        for n in names:
            for j, h in enumerate(low):
                if n in h:
                    return j
        return None

    i_tk = col("ticker", "symbol", "instrument", "conid")
    i_sh = col("shares", "quantity", "qty", "units", "position")
    i_co = col("avg", "cost", "basis", "purchase", "average price")
    if i_tk is None:
        return None, ["Could not find a ticker / symbol column."]
    positions = []
    for r in rows[1:]:
        if len(r) <= i_tk:
            continue
        tk = r[i_tk].strip().upper()
        if not tk:
            continue
        s = 0.0
        if i_sh is not None and i_sh < len(r) and r[i_sh].strip():
            try:
                s = float(r[i_sh])
            except Exception:
                s = 0.0
        c = 0.0
        if i_co is not None and i_co < len(r) and r[i_co].strip():
            try:
                c = float(r[i_co])
            except Exception:
                c = 0.0
        if s <= 0:
            continue
        positions.append({
            "ticker": tk,
            "shares": s,
            "avg_cost": max(c, 0.01),
        })
    if not positions:
        return None, ["No usable position rows were found."]
    return positions, []


# ------------------------------------------------------------
# Top level: detect + route
# ------------------------------------------------------------

def parse_import_file(file):
    try:
        rows = _read_rows(file)
    except Exception:
        return {
            "positions": None,
            "warnings": [],
            "fmt": "error",
            "error": "Could not read the file.",
        }
    fmt = _detect_format(rows)
    if fmt == "ibkr":
        pos, warns = _parse_ibkr(rows)
    elif fmt == "transactions":
        pos, warns = _parse_transactions(rows)
    elif fmt == "holdings":
        pos, warns = _parse_holdings(rows)
    else:
        return {
            "positions": None,
            "warnings": [],
            "fmt": "empty",
            "error": "The file appears to be empty.",
        }
    err = None
    if not pos:
        err = warns[-1] if warns else "Nothing to import from this file."
    return {
        "positions": pos or [],
        "warnings": warns,
        "fmt": fmt,
        "error": err,
    }


# ------------------------------------------------------------
# The Settings-page UI for the importer
# ------------------------------------------------------------

FMT_LABEL = {
    "ibkr": "Interactive Brokers Activity Statement (exact)",
    "transactions": "Transaction history (estimate - review carefully)",
    "holdings": "Holdings snapshot (exact)",
    "empty": "Empty file",
    "error": "Unreadable file",
}


def render_csv_import():
    up = st.file_uploader("Upload broker CSV", type=["csv"], key="csv_up")
    if up is None:
        return
    res = parse_import_file(up)
    st.markdown("**Detected format:** " + str(FMT_LABEL.get(res["fmt"], res["fmt"])))
    for w in res["warnings"]:
        st.warning(w)
    if res["error"]:
        st.error(res["error"])
    positions = res["positions"]
    if not positions:
        return
    prev = pd.DataFrame(positions, columns=["ticker", "shares", "avg_cost"])
    st.markdown("**Preview - " + str(len(prev)) + " position(s)**")
    st.dataframe(prev, use_container_width=True, hide_index=True)
    csv_mode = st.radio(
        "Import mode",
        ["Merge / update by ticker (keep the rest)", "Replace my whole portfolio"],
        horizontal=True,
        key="csv_mode",
    )
    with st.form("csv_confirm"):
        go = st.form_submit_button("Apply import", type="primary")
        if go:
            if csv_mode.startswith("Replace"):
                st.session_state["active_positions"] = positions[:MAX_ACTIVE]
            else:
                by_tk = {p["ticker"]: p for p in st.session_state.get("active_positions", [])}
                for r in positions:
                    by_tk[r["ticker"]] = r
                st.session_state["active_positions"] = list(by_tk.values())[:MAX_ACTIVE]
            kept = len(st.session_state["active_positions"])
            msg = "Imported " + str(len(positions)) + " position(s); cockpit now holds " + str(kept) + " (max " + str(MAX_ACTIVE) + "). Review and correct any flagged figures."
            st.success(msg)
            st.rerun()
