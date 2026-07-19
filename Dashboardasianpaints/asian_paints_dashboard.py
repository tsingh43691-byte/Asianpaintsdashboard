"""
ASIAN PAINTS LTD — Interactive Financial Model Dashboard
3-Statement Model | DCF Valuation | Sensitivity Analysis

Run:
    pip install streamlit plotly pandas numpy
    streamlit run asian_paints_dashboard.py

All historicals (FY21-FY25) sourced from consolidated financials
(stockanalysis.com / S&P Global Market Intelligence, screener.in).
Figures in INR Crores unless stated. FY = Apr-Mar.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Asian Paints | 3-Statement + DCF Model", layout="wide")

# =========================================================
# 1. HISTORICAL DATA (actuals, INR Crores)
# =========================================================
years_hist = ["FY21", "FY22", "FY23", "FY24", "FY25"]

hist = pd.DataFrame({
    "Revenue":        [21504, 28982, 34430, 35438, 33859],
    "EBITDA":         [4613, 4539, 6020, 7233, 5604],
    "D&A":            [549, 551, 557, 490, 624],
    "Net Income":     [3139, 3031, 4107, 5460, 3667],
    "Total Debt":     [1587, 1587, 1933, 2474, 2290],
    "Cash & Invest":  [3611, 4037, 3507, 5432, 4692],
    "Working Cap":    [7581, 7581, 8639, 9036, 8850],
}, index=years_hist)

hist["EBITDA Margin %"] = (hist["EBITDA"] / hist["Revenue"] * 100).round(1)
hist["Net Margin %"] = (hist["Net Income"] / hist["Revenue"] * 100).round(1)

SHARES_OUT = 95.92          # crore shares (959.2 mn)
CURRENT_PRICE = 2700        # INR — update to live market price if needed
BASE_REV = 33859            # FY25 actual revenue (Cr)
BASE_EBITDA_MARGIN = 16.55  # FY25 actual
BASE_NET_DEBT = -2402       # FY25: net CASH of 2402 Cr (negative debt)

# =========================================================
# SIDEBAR — ASSUMPTIONS (drives everything below)
# =========================================================
st.sidebar.header("🎛️ Model Assumptions")

st.sidebar.subheader("Revenue & Margins")
rev_growth = st.sidebar.slider("Revenue CAGR — FY26-30 (%)", 4.0, 18.0, 10.0, 0.5)
ebitda_margin_target = st.sidebar.slider("Target EBITDA Margin by FY30 (%)", 14.0, 22.0, 19.0, 0.5)
tax_rate = st.sidebar.slider("Effective Tax Rate (%)", 20.0, 30.0, 25.2, 0.1)

st.sidebar.subheader("Capital Intensity")
capex_pct = st.sidebar.slider("Capex (% of Revenue)", 2.0, 8.0, 4.0, 0.25)
da_pct = st.sidebar.slider("D&A (% of Revenue)", 1.0, 4.0, 1.8, 0.1)
wc_pct_change = st.sidebar.slider("Incr. Working Capital (% of Δ Revenue)", 0.0, 30.0, 15.0, 1.0)

st.sidebar.subheader("DCF Inputs")
wacc = st.sidebar.slider("WACC (%)", 8.0, 15.0, 11.0, 0.25)
terminal_growth = st.sidebar.slider("Terminal Growth Rate (%)", 3.0, 7.0, 5.0, 0.25)
forecast_years = 5

st.sidebar.caption("Adjust sliders → the entire model (3-statement, FCF, DCF, football-field) recalculates live.")

# =========================================================
# 2. THREE-STATEMENT PROJECTION ENGINE (FY26–FY30)
# =========================================================
proj_years = [f"FY{26+i}" for i in range(forecast_years)]

revenue = [BASE_REV]
for i in range(forecast_years):
    revenue.append(revenue[-1] * (1 + rev_growth/100))
revenue = revenue[1:]  # FY26..FY30

# margin glides linearly from FY25 actual to target by FY30
margins = np.linspace(BASE_EBITDA_MARGIN, ebitda_margin_target, forecast_years)

ebitda = [r*m/100 for r, m in zip(revenue, margins)]
da = [r*da_pct/100 for r in revenue]
ebit = [e - d for e, d in zip(ebitda, da)]
tax = [max(x,0)*tax_rate/100 for x in ebit]
nopat = [x - t for x, t in zip(ebit, tax)]
net_income = nopat  # simplified: ignoring interest/other income for core FCFF build

capex = [r*capex_pct/100 for r in revenue]

rev_with_base = [BASE_REV] + revenue
delta_rev = [rev_with_base[i+1]-rev_with_base[i] for i in range(forecast_years)]
delta_wc = [dr*wc_pct_change/100 for dr in delta_rev]

# Free Cash Flow to Firm = NOPAT + D&A - Capex - ΔWC
fcff = [ni + d - cx - dwc for ni, d, cx, dwc in zip(nopat, da, capex, delta_wc)]

proj = pd.DataFrame({
    "Revenue": revenue,
    "EBITDA": ebitda,
    "EBITDA Margin %": margins,
    "D&A": da,
    "EBIT": ebit,
    "Tax": tax,
    "NOPAT": net_income,
    "Capex": capex,
    "ΔWorking Capital": delta_wc,
    "FCFF": fcff,
}, index=proj_years).round(1)

# Simplified projected Balance Sheet & Cash Flow (illustrative, ties to FCFF build)
cum_wc = np.cumsum(delta_wc) + hist["Working Cap"].iloc[-1]
net_ppe = np.cumsum(np.array(capex) - np.array(da)) + 9886  # FY25 PP&E base (Cr)
cash_build = np.cumsum(fcff) + 4692  # rough: FY25 cash base + cumulative FCFF (no dividend/debt paydown netted)

bs_proj = pd.DataFrame({
    "Net PP&E": net_ppe,
    "Working Capital": cum_wc,
    "Cash (approx.)": cash_build,
}, index=proj_years).round(0)

cf_proj = pd.DataFrame({
    "NOPAT": net_income,
    "+ D&A": da,
    "- Capex": [-c for c in capex],
    "- ΔWC": [-w for w in delta_wc],
    "= FCFF": fcff,
}, index=proj_years).round(1)

# =========================================================
# 3. DCF VALUATION
# =========================================================
discount_factors = [(1+wacc/100)**-(i+1) for i in range(forecast_years)]
pv_fcff = [f*df for f, df in zip(fcff, discount_factors)]

terminal_value = fcff[-1]*(1+terminal_growth/100) / (wacc/100 - terminal_growth/100)
pv_terminal = terminal_value * discount_factors[-1]

enterprise_value = sum(pv_fcff) + pv_terminal
equity_value = enterprise_value - BASE_NET_DEBT  # BASE_NET_DEBT negative (net cash) -> adds back
intrinsic_price = equity_value / SHARES_OUT
upside = (intrinsic_price/CURRENT_PRICE - 1)*100

# =========================================================
# 4. SENSITIVITY TABLE (WACC x Terminal Growth)
# =========================================================
wacc_range = np.round(np.arange(wacc-1.5, wacc+2.0, 0.75), 2)
tg_range = np.round(np.arange(terminal_growth-1.0, terminal_growth+1.25, 0.5), 2)

sens = pd.DataFrame(index=[f"{w}%" for w in wacc_range], columns=[f"{t}%" for t in tg_range])
for w in wacc_range:
    for t in tg_range:
        if w/100 <= t/100:
            sens.loc[f"{w}%", f"{t}%"] = np.nan
            continue
        dfs = [(1+w/100)**-(i+1) for i in range(forecast_years)]
        pv = sum(f*d for f, d in zip(fcff, dfs))
        tv = fcff[-1]*(1+t/100)/(w/100 - t/100)
        ev = pv + tv*dfs[-1]
        eq = ev - BASE_NET_DEBT
        sens.loc[f"{w}%", f"{t}%"] = round(eq/SHARES_OUT, 0)

# =========================================================
# ================= DASHBOARD LAYOUT =====================
# =========================================================
st.title("🎨 Asian Paints Ltd — Financial Model & Valuation Dashboard")
st.caption("Consolidated financials · FY21–FY25 actuals · FY26–FY30 projected · DCF-based intrinsic valuation")

# ---- KPI CARDS ----
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Current Market Price", f"₹{CURRENT_PRICE:,.0f}")
k2.metric("DCF Intrinsic Value/Share", f"₹{intrinsic_price:,.0f}", f"{upside:+.1f}%")
k3.metric("Enterprise Value", f"₹{enterprise_value:,.0f} Cr")
k4.metric("Equity Value", f"₹{equity_value:,.0f} Cr")
k5.metric("FY30E Revenue", f"₹{revenue[-1]:,.0f} Cr", f"{rev_growth:.1f}% CAGR")

verdict = "UNDERVALUED ✅" if upside > 5 else ("OVERVALUED ⚠️" if upside < -5 else "FAIRLY VALUED ➖")
st.info(f"**Verdict at current assumptions: {verdict}**  |  Implied upside/downside vs CMP: **{upside:+.1f}%**")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Historicals", "📈 3-Statement Projection", "💰 DCF Valuation",
    "🔥 Sensitivity", "📉 Ratio & Trend Analysis"
])

# ---------------- TAB 1: HISTORICALS ----------------
with tab1:
    st.subheader("Historical Financials (FY21–FY25, Consolidated, ₹ Cr)")
    st.dataframe(hist.style.format("{:.0f}", subset=[c for c in hist.columns if "%" not in c])
                 .format("{:.1f}%", subset=[c for c in hist.columns if "%" in c]),
                 use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_bar(x=years_hist, y=hist["Revenue"], name="Revenue", marker_color="#1f77b4")
        fig.add_bar(x=years_hist, y=hist["EBITDA"], name="EBITDA", marker_color="#ff7f0e")
        fig.update_layout(title="Revenue vs EBITDA (₹ Cr)", barmode="group", height=380)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = go.Figure()
        fig2.add_scatter(x=years_hist, y=hist["EBITDA Margin %"], name="EBITDA Margin %", mode="lines+markers")
        fig2.add_scatter(x=years_hist, y=hist["Net Margin %"], name="Net Margin %", mode="lines+markers")
        fig2.update_layout(title="Margin Trend (%)", height=380)
        st.plotly_chart(fig2, use_container_width=True)

    st.caption("Note: Revenue dip in FY25 reflects muted decorative-paints demand, down-trading and rising competitive "
               "intensity (Grasim/Birla Opus entry). EBITDA margin compressed ~385 bps YoY.")

# ---------------- TAB 2: 3-STATEMENT PROJECTION ----------------
with tab2:
    st.subheader(f"Projected Income Statement — FY26–FY30 (₹ Cr)")
    st.dataframe(proj.style.format("{:.1f}"), use_container_width=True)

    st.subheader("Simplified Projected Balance Sheet (₹ Cr)")
    st.dataframe(bs_proj.style.format("{:.0f}"), use_container_width=True)

    st.subheader("Free Cash Flow Build (₹ Cr)")
    st.dataframe(cf_proj.style.format("{:.1f}"), use_container_width=True)

    fig3 = px.bar(proj, x=proj.index, y=["EBITDA", "FCFF"], barmode="group",
                  title="Projected EBITDA vs FCFF (₹ Cr)")
    st.plotly_chart(fig3, use_container_width=True)

    st.caption("Audit check: NOPAT + D&A − Capex − ΔWC = FCFF, tied out row-wise above. "
               "Adjust sliders in the sidebar to stress-test margin recovery / capex cycle assumptions.")

# ---------------- TAB 3: DCF ----------------
with tab3:
    st.subheader("Discounted Cash Flow Valuation")

    dcf_table = pd.DataFrame({
        "FCFF (₹ Cr)": fcff,
        "Discount Factor": discount_factors,
        "PV of FCFF (₹ Cr)": pv_fcff,
    }, index=proj_years).round(2)
    st.dataframe(dcf_table, use_container_width=True)

    b1, b2 = st.columns(2)
    with b1:
        st.markdown(f"""
        | DCF Bridge | ₹ Cr |
        |---|---|
        | **Sum of PV of explicit FCFF (FY26-30)** | {sum(pv_fcff):,.0f} |
        | **Terminal Value (undiscounted)** | {terminal_value:,.0f} |
        | **PV of Terminal Value** | {pv_terminal:,.0f} |
        | **Enterprise Value** | **{enterprise_value:,.0f}** |
        | (–) Net Debt / (+) Net Cash | {-BASE_NET_DEBT:,.0f} |
        | **Equity Value** | **{equity_value:,.0f}** |
        | ÷ Shares Outstanding (Cr) | {SHARES_OUT:,.1f} |
        | **Intrinsic Value / Share** | **₹{intrinsic_price:,.0f}** |
        """)
    with b2:
        fig4 = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative"]*forecast_years + ["relative", "total"],
            x=proj_years + ["PV Terminal Value", "Enterprise Value"],
            y=pv_fcff + [pv_terminal, 0],
            connector={"line": {"color": "grey"}},
        ))
        fig4.update_layout(title="DCF Value Build-up (₹ Cr)", height=420)
        st.plotly_chart(fig4, use_container_width=True)

    st.caption(f"Terminal Value = FCFF(FY30) × (1+g) / (WACC−g), assuming a {terminal_growth:.1f}% perpetual growth "
               f"and {wacc:.1f}% WACC — reflecting India cost of equity for a large-cap consumer discretionary.")

# ---------------- TAB 4: SENSITIVITY ----------------
with tab4:
    st.subheader("Sensitivity: Intrinsic Value/Share — WACC (rows) vs Terminal Growth (columns)")
    st.dataframe(sens.style.background_gradient(cmap="RdYlGn", axis=None).format("{:.0f}", na_rep="—"),
                 use_container_width=True)
    st.caption("Diagonal blanks occur where WACC ≤ terminal growth (mathematically invalid Gordon Growth case).")

    st.subheader("Football Field — Value per Share Range")
    ff_labels = ["Bear (WACC+1.5%, g-1%)", "Base Case", "Bull (WACC-1.5%, g+1%)", "Current Market Price"]
    def _val(w_delta, g_delta):
        w2, t2 = wacc+w_delta, terminal_growth+g_delta
        dfs = [(1+w2/100)**-(i+1) for i in range(forecast_years)]
        pv = sum(f*d for f, d in zip(fcff, dfs))
        tv = fcff[-1]*(1+t2/100)/(w2/100-t2/100)
        ev = pv + tv*dfs[-1]
        return (ev - BASE_NET_DEBT)/SHARES_OUT
    ff_values = [_val(1.5,-1), _val(0,0), _val(-1.5,1), CURRENT_PRICE]
    fig5 = go.Figure(go.Bar(x=ff_values, y=ff_labels, orientation="h",
                             marker_color=["#d62728","#1f77b4","#2ca02c","#7f7f7f"]))
    fig5.update_layout(title="Valuation Range (₹/share)", height=320)
    st.plotly_chart(fig5, use_container_width=True)

# ---------------- TAB 5: RATIOS ----------------
with tab5:
    st.subheader("Key Ratio Analysis")
    ratios = pd.DataFrame({
        "ROE (Net Income/Equity, indicative %)": [15.6, 15.1, 18.0, 20.6, 15.6],
        "Net Debt/EBITDA (x)": [(hist['Total Debt'][y]-hist['Cash & Invest'][y])/hist['EBITDA'][y] for y in years_hist],
        "EBITDA Margin %": hist["EBITDA Margin %"],
        "Net Margin %": hist["Net Margin %"],
    }, index=years_hist)
    st.dataframe(ratios.style.format("{:.2f}"), use_container_width=True)

    st.markdown("""
**Key investor takeaways:**
- Asian Paints has a **net-cash balance sheet** (net cash > debt) — very low leverage risk.
- FY25 margin compression is the central debate: driven by rising competition (Birla Opus/Grasim entry, JSW Paints) and demand slowdown — recovery trajectory in your margin-glide assumption is the single biggest swing factor in this DCF.
- Valuation currently trades at a rich EV/EBITDA multiple historically — the DCF here provides an independent cross-check versus market multiples.
- **Bear/Bull sensitivity range** in the Football Field tab shows how much intrinsic value swings with WACC/terminal growth — always present a **range**, never a single-point target, in a professional ER report.
    """)

st.divider()
st.caption("⚠️ Educational model built on public consolidated financials. Not investment advice. "
           "Verify live price, latest quarter numbers, and management commentary before any investment decision.")