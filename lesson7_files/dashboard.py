"""
dashboard.py
E-commerce Business Analytics — Streamlit Dashboard
"""

import os
import sys
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from data_loader import load_and_process_data
from business_metrics import (
    calculate_revenue_metrics,
    calculate_monthly_revenue,
    calculate_product_metrics,
    calculate_geographic_metrics,
    calculate_delivery_metrics,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="E-commerce Analytics",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global styles ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    /* ── Cards ── */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 18px 22px;
        min-height: 120px;
        height: 120px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        box-sizing: border-box;
    }
    .bottom-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 20px 24px;
        min-height: 130px;
        height: 130px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        box-sizing: border-box;
    }

    /* ── Typography ── */
    .card-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 5px;
    }
    .card-value {
        font-size: 28px;
        font-weight: 700;
        color: #111827;
        line-height: 1.2;
        margin-bottom: 5px;
    }
    .trend-up   { font-size: 12px; font-weight: 600; color: #16a34a; }
    .trend-down { font-size: 12px; font-weight: 600; color: #dc2626; }
    .card-sub   { font-size: 12px; color: #9ca3af; }
    .stars      { font-size: 20px; color: #f59e0b; letter-spacing: 3px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Data loading (cached) ─────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str = "ecommerce_data/"):
    loader, processed = load_and_process_data(path)
    return loader, processed


loader, processed = load_data()
_min_date = processed["order_purchase_timestamp"].min().date()
_max_date = processed["order_purchase_timestamp"].max().date()


# ── Header ────────────────────────────────────────────────────────────────────
hcol1, hcol2 = st.columns([3, 1])
with hcol1:
    st.markdown("## E-commerce Business Analytics")
with hcol2:
    date_range = st.date_input(
        "Date Range",
        value=(date(2023, 1, 1), date(2023, 12, 31)),
        min_value=_min_date,
        max_value=_max_date,
    )

# Parse date range — handle mid-selection (only 1 date picked)
if isinstance(date_range, (list, tuple)):
    if len(date_range) == 2:
        start_dt = pd.Timestamp(date_range[0])
        end_dt   = pd.Timestamp(date_range[1])
    elif len(date_range) == 1:
        start_dt = end_dt = pd.Timestamp(date_range[0])
    else:
        start_dt = pd.Timestamp(date(2023, 1, 1))
        end_dt   = pd.Timestamp(date(2023, 12, 31))
else:
    start_dt = pd.Timestamp(date(2023, 1, 1))
    end_dt   = pd.Timestamp(date(2023, 12, 31))

# Comparison period: same window shifted back 1 year
try:
    comp_start = start_dt.replace(year=start_dt.year - 1)
    comp_end   = end_dt.replace(year=end_dt.year - 1)
except ValueError:          # leap-day edge case
    comp_start = start_dt - pd.DateOffset(years=1)
    comp_end   = end_dt   - pd.DateOffset(years=1)

cur_year  = end_dt.year
comp_year = cur_year - 1


# ── Filter helpers ────────────────────────────────────────────────────────────
def _filter(df: pd.DataFrame, s: pd.Timestamp, e: pd.Timestamp) -> pd.DataFrame:
    mask = (
        (df["order_purchase_timestamp"] >= s)
        & (df["order_purchase_timestamp"] <= e)
        & (df["order_status"] == "delivered")
    )
    return df[mask].reset_index(drop=True)


sales_cur  = _filter(processed, start_dt, end_dt)
sales_comp = _filter(processed, comp_start, comp_end)

if sales_cur.empty:
    st.warning("No delivered orders found for the selected date range. Please adjust the filter.")
    st.stop()

# Keep an empty-but-schema-correct DataFrame if no comparison data exists
if sales_comp.empty:
    sales_comp = pd.DataFrame(columns=sales_cur.columns)


# ── Compute metrics ───────────────────────────────────────────────────────────
rev_m    = calculate_revenue_metrics(sales_cur, sales_comp, cur_year, comp_year)
monthly  = calculate_monthly_revenue(sales_cur)
prod_m   = calculate_product_metrics(sales_cur)
geo_m    = calculate_geographic_metrics(sales_cur)
del_m    = calculate_delivery_metrics(sales_cur)

del_m_comp: dict | None = None
if not sales_comp.empty:
    try:
        del_m_comp = calculate_delivery_metrics(sales_comp)
    except Exception:
        pass


# ── Format helpers ────────────────────────────────────────────────────────────
def fmt_money(v: float) -> str:
    """Compact dollar amount for KPI cards."""
    if v >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v / 1_000:.1f}K"
    return f"${v:.2f}"


def fmt_axis(v: float) -> str:
    """Compact dollar amount for chart axes / bar labels."""
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:.0f}"


def trend_html(pct, inverted: bool = False) -> str:
    """
    Return an HTML trend badge.
    `inverted=True` swaps the colour logic (used for delivery days where lower = better).
    """
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return '<span class="card-sub">No comparison data</span>'
    is_good = (pct <= 0) if inverted else (pct >= 0)
    arrow   = "▲" if pct >= 0 else "▼"
    cls     = "trend-up" if is_good else "trend-down"
    return f'<span class="{cls}">{arrow} {abs(pct):.2f}% vs prior period</span>'


# ── KPI row ───────────────────────────────────────────────────────────────────
total_rev    = rev_m[f"total_revenue_{cur_year}"]
rev_growth   = rev_m["revenue_growth_pct"]
aov          = rev_m[f"aov_{cur_year}"]
aov_growth   = rev_m["aov_growth_pct"]
total_orders = rev_m[f"total_orders_{cur_year}"]
ord_growth   = rev_m["order_growth_pct"]

avg_mom_raw = monthly["mom_growth_pct"].mean()
avg_mom_str = f"{avg_mom_raw:+.2f}%" if not np.isnan(avg_mom_raw) else "N/A"

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f"""<div class="kpi-card">
          <div class="card-label">Total Revenue</div>
          <div class="card-value">{fmt_money(total_rev)}</div>
          {trend_html(rev_growth)}
        </div>""",
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""<div class="kpi-card">
          <div class="card-label">Monthly Growth</div>
          <div class="card-value">{avg_mom_str}</div>
          <div class="card-sub">Avg month-over-month</div>
        </div>""",
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""<div class="kpi-card">
          <div class="card-label">Avg Order Value</div>
          <div class="card-value">{fmt_money(aov)}</div>
          {trend_html(aov_growth)}
        </div>""",
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f"""<div class="kpi-card">
          <div class="card-label">Total Orders</div>
          <div class="card-value">{total_orders:,}</div>
          {trend_html(ord_growth)}
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)


# ── Chart constants ───────────────────────────────────────────────────────────
CHART_H    = 380
BG         = "white"
GRID_C     = "#e5e7eb"       # slightly darker grid for contrast on white
PRIMARY    = "#1e4976"        # deeper blue for better contrast
SECONDARY  = "#4e8fc4"
FONT_COLOR = "#111827"        # near-black for all chart text
AXIS_COLOR = "#374151"        # dark gray for axis labels / ticks
MTHS       = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

# Shared layout defaults applied to every figure (no margin — set per chart)
_BASE = dict(
    font=dict(color=FONT_COLOR, size=12, family="system-ui, -apple-system, sans-serif"),
    plot_bgcolor=BG,
    paper_bgcolor=BG,
    height=CHART_H,
)
_MARGIN      = dict(l=10, r=10,  t=58, b=10)   # default margin
_MARGIN_WIDE = dict(l=10, r=80,  t=58, b=10)   # extra right room for bar labels

def _title(text: str) -> dict:
    return dict(text=text, font=dict(size=15, color=FONT_COLOR, weight="bold"), x=0, xanchor="left", pad=dict(l=4))

def _xaxis(**kw) -> dict:
    base = dict(tickfont=dict(color=AXIS_COLOR, size=11), title_font=dict(color=AXIS_COLOR, size=12))
    base.update(kw)
    return base

def _yaxis(**kw) -> dict:
    base = dict(tickfont=dict(color=AXIS_COLOR, size=11), title_font=dict(color=AXIS_COLOR, size=12), zeroline=False)
    base.update(kw)
    return base


# ── Charts grid — row 1 ───────────────────────────────────────────────────────
gc1, gc2 = st.columns(2)

# Chart 1: Revenue trend (solid = current, dashed = comparison)
with gc1:
    cur_m  = calculate_monthly_revenue(sales_cur)
    comp_m = (
        calculate_monthly_revenue(sales_comp)
        if not sales_comp.empty
        else pd.DataFrame(columns=["purchase_month", "revenue"])
    )
    cur_m["label"]  = cur_m["purchase_month"].map(MTHS)
    if not comp_m.empty:
        comp_m["label"] = comp_m["purchase_month"].map(MTHS)

    all_revs = list(cur_m["revenue"]) + (
        list(comp_m["revenue"]) if not comp_m.empty else []
    )
    # Zoom y-axis to show trend variation (don't start at 0)
    y_min_data = min(all_revs) if all_revs else 0
    y_max_data = max(all_revs) if all_revs else 1
    y_pad      = (y_max_data - y_min_data) * 0.15
    y_lo       = max(0, y_min_data - y_pad)
    y_hi       = y_max_data + y_pad
    y_ticks    = np.linspace(y_lo, y_hi, 6)
    y_labels   = [fmt_axis(v) for v in y_ticks]

    f1 = go.Figure()
    f1.add_trace(
        go.Scatter(
            x=cur_m["label"],
            y=cur_m["revenue"],
            name=str(cur_year),
            mode="lines+markers",
            line=dict(color=PRIMARY, width=2.5, dash="solid"),
            marker=dict(size=7, color=PRIMARY),
        )
    )
    if not comp_m.empty:
        f1.add_trace(
            go.Scatter(
                x=comp_m["label"],
                y=comp_m["revenue"],
                name=str(comp_year),
                mode="lines+markers",
                line=dict(color=SECONDARY, width=2, dash="dash"),
                marker=dict(size=6, symbol="square", color=SECONDARY),
            )
        )
    f1.update_layout(
        **_BASE,
        margin=_MARGIN,
        title=_title(f"Monthly Revenue: {cur_year} vs {comp_year}"),
        xaxis=_xaxis(showgrid=True, gridcolor=GRID_C, gridwidth=1),
        yaxis=_yaxis(
            showgrid=True,
            gridcolor=GRID_C,
            gridwidth=1,
            tickvals=y_ticks,
            ticktext=y_labels,
            range=[y_lo, y_hi],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(color=FONT_COLOR, size=12),
            bgcolor="rgba(255,255,255,0)",
        ),
    )
    st.plotly_chart(f1, use_container_width=True)

# Chart 2: Top 10 categories — sorted descending, blue gradient
with gc2:
    top10 = prod_m.head(10).sort_values("revenue", ascending=True)
    n = len(top10)
    # Light blue for lowest → deep blue for highest (plotly renders bottom→top)
    grad_colors = [
        f"rgba(30,73,118,{0.22 + 0.78 * (i / max(n - 1, 1))})" for i in range(n)
    ]
    max_cat  = top10["revenue"].max()
    x_ticks  = np.linspace(0, max_cat * 1.20, 6)
    x_labels = [fmt_axis(v) for v in x_ticks]

    f2 = go.Figure(
        go.Bar(
            x=top10["revenue"],
            y=top10["product_category_name"],
            orientation="h",
            marker_color=grad_colors,
            text=[fmt_axis(v) for v in top10["revenue"]],
            textposition="outside",
            textfont=dict(color=FONT_COLOR, size=11),
            cliponaxis=False,
        )
    )
    f2.update_layout(
        **_BASE,
        margin=_MARGIN_WIDE,
        title=_title("Top 10 Revenue Categories"),
        xaxis=_xaxis(
            showgrid=True,
            gridcolor=GRID_C,
            tickvals=x_ticks,
            ticktext=x_labels,
            range=[0, max_cat * 1.30],
        ),
        yaxis=_yaxis(showgrid=False, tickfont=dict(color=FONT_COLOR, size=11)),
        showlegend=False,
    )
    st.plotly_chart(f2, use_container_width=True)


# ── Charts grid — row 2 ───────────────────────────────────────────────────────
gc3, gc4 = st.columns(2)

# Chart 3: Revenue by state choropleth
with gc3:
    f3 = px.choropleth(
        geo_m,
        locations="customer_state",
        color="revenue",
        locationmode="USA-states",
        scope="usa",
        color_continuous_scale="Blues",
        title="Revenue by State",
        custom_data=["customer_state", "revenue", "order_count", "aov"],
    )
    f3.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Revenue: $%{customdata[1]:,.0f}<br>"
            "Orders: %{customdata[2]:,}<br>"
            "AOV: $%{customdata[3]:.2f}"
            "<extra></extra>"
        )
    )
    f3.update_layout(
        font=dict(color=FONT_COLOR, size=12),
        coloraxis_colorbar=dict(
            title=dict(text="Revenue ($)", font=dict(color=FONT_COLOR, size=12)),
            tickformat="$,.0f",
            tickfont=dict(color=AXIS_COLOR, size=11),
        ),
        margin=dict(l=0, r=0, t=58, b=0),
        height=CHART_H,
        title=_title("Revenue by State"),
        paper_bgcolor=BG,
    )
    st.plotly_chart(f3, use_container_width=True)

# Chart 4: Avg review score by delivery time bucket
with gc4:
    bkt = del_m["delivery_bucket_summary"]
    y_lo = max(0.0, float(bkt["avg_review_score"].min()) - 0.20)
    y_hi = min(5.0, float(bkt["avg_review_score"].max()) + 0.25)

    f4 = go.Figure(
        go.Bar(
            x=bkt["delivery_time"].astype(str),
            y=bkt["avg_review_score"],
            marker_color=PRIMARY,
            text=[f"{s:.2f}" for s in bkt["avg_review_score"]],
            textposition="outside",
            textfont=dict(color=FONT_COLOR, size=14, family="system-ui, -apple-system, sans-serif"),
            width=0.40,
        )
    )
    _axis_title_font = dict(color=FONT_COLOR, size=13, family="system-ui, -apple-system, sans-serif")
    f4.update_layout(
        **_BASE,
        margin=dict(l=60, r=20, t=58, b=60),
        title=_title("Satisfaction vs Delivery Time"),
        xaxis=dict(
            title=dict(text="Delivery Time", font=_axis_title_font),
            tickfont=dict(color=FONT_COLOR, size=13),
            showgrid=False,
            linecolor="#d1d5db",
            linewidth=1,
        ),
        yaxis=dict(
            title=dict(text="Avg Review Score (1–5)", font=_axis_title_font),
            tickfont=dict(color=FONT_COLOR, size=12),
            showgrid=True,
            gridcolor=GRID_C,
            gridwidth=1,
            range=[y_lo, y_hi],
            zeroline=False,
        ),
        showlegend=False,
    )
    st.plotly_chart(f4, use_container_width=True)

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ── Bottom row ────────────────────────────────────────────────────────────────
bc1, bc2 = st.columns(2)

with bc1:
    avg_days = del_m["avg_delivery_days"]
    if del_m_comp is not None:
        comp_days = del_m_comp["avg_delivery_days"]
        days_pct  = (
            (avg_days - comp_days) / comp_days * 100 if comp_days else None
        )
        td_html = trend_html(days_pct, inverted=True)
    else:
        td_html = '<span class="card-sub">No comparison data</span>'

    st.markdown(
        f"""<div class="bottom-card">
          <div class="card-label">Average Delivery Time</div>
          <div class="card-value">{avg_days} days</div>
          {td_html}
        </div>""",
        unsafe_allow_html=True,
    )

with bc2:
    score     = del_m["avg_review_score"]
    full_star = int(score)
    stars_str = "★" * full_star + "☆" * (5 - full_star)

    st.markdown(
        f"""<div class="bottom-card">
          <div class="card-label">Review Score</div>
          <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:4px;">
            <div class="card-value">{score}</div>
            <div class="stars">{stars_str}</div>
          </div>
          <div class="card-sub">Average Review Score</div>
        </div>""",
        unsafe_allow_html=True,
    )
