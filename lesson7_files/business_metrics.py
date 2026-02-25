"""
business_metrics.py
-------------------
Pure calculation and visualisation functions for e-commerce business metrics.
All functions accept plain DataFrames so they can be used independently of the
data_loader module.

Metrics covered
---------------
- Revenue       : total, YoY growth, month-over-month trend, average order value
- Products      : revenue by category, market share
- Geography     : revenue and order count by state
- Customer exp. : review score distribution, delivery speed analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import plotly.express as px

# ---------------------------------------------------------------------------
# Shared style constants
# ---------------------------------------------------------------------------

PRIMARY_COLOR   = '#2C5F8A'   # dark blue  – main bars / lines
SECONDARY_COLOR = '#5BA4CF'   # mid blue   – comparison series
ACCENT_COLOR    = '#F4A460'   # sandy      – highlights
NEG_COLOR       = '#C0392B'   # red        – negative values
POS_COLOR       = '#27AE60'   # green      – positive values
GRID_COLOR      = '#E8E8E8'

FIGURE_SIZE_WIDE = (12, 5)
FIGURE_SIZE_SQ   = (10, 6)


def _apply_base_style(ax, title: str, xlabel: str = '', ylabel: str = '') -> None:
    """Apply consistent axis styling (title, labels, grid, spines)."""
    ax.set_title(title, fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.yaxis.grid(True, color=GRID_COLOR, linestyle='--', linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)


# ===========================================================================
# 1. Revenue Metrics
# ===========================================================================

def calculate_revenue_metrics(
    current_sales: pd.DataFrame,
    comparison_sales: pd.DataFrame,
    current_year: int,
    comparison_year: int,
) -> dict:
    """
    Calculate top-level revenue KPIs comparing two years.

    Parameters
    ----------
    current_sales : pd.DataFrame
        Filtered sales dataset for the year being analysed.
    comparison_sales : pd.DataFrame
        Filtered sales dataset for the comparison year.
    current_year : int
    comparison_year : int

    Returns
    -------
    dict with keys:
        current_year, comparison_year,
        total_revenue_{current_year}, total_revenue_{comparison_year},
        revenue_growth_pct,
        total_orders_{current_year}, total_orders_{comparison_year},
        order_growth_pct,
        aov_{current_year}, aov_{comparison_year},
        aov_growth_pct
    """
    rev_cur  = current_sales['price'].sum()
    rev_comp = comparison_sales['price'].sum()

    orders_cur  = current_sales['order_id'].nunique()
    orders_comp = comparison_sales['order_id'].nunique()

    aov_cur  = current_sales.groupby('order_id')['price'].sum().mean()
    aov_comp = comparison_sales.groupby('order_id')['price'].sum().mean()

    def pct_change(new, old):
        return ((new - old) / old * 100) if old else None

    return {
        'current_year':   current_year,
        'comparison_year': comparison_year,
        f'total_revenue_{current_year}':    round(rev_cur, 2),
        f'total_revenue_{comparison_year}': round(rev_comp, 2),
        'revenue_growth_pct': round(pct_change(rev_cur, rev_comp), 2),
        f'total_orders_{current_year}':    orders_cur,
        f'total_orders_{comparison_year}': orders_comp,
        'order_growth_pct': round(pct_change(orders_cur, orders_comp), 2),
        f'aov_{current_year}':    round(aov_cur, 2),
        f'aov_{comparison_year}': round(aov_comp, 2),
        'aov_growth_pct': round(pct_change(aov_cur, aov_comp), 2),
    }


def calculate_monthly_revenue(sales: pd.DataFrame) -> pd.DataFrame:
    """
    Compute monthly revenue totals and month-over-month percentage change.

    Parameters
    ----------
    sales : pd.DataFrame
        Sales dataset containing 'purchase_month' and 'price' columns.

    Returns
    -------
    pd.DataFrame with columns: purchase_month, revenue, mom_growth_pct
    """
    monthly = (
        sales.groupby('purchase_month')['price']
        .sum()
        .reset_index()
        .rename(columns={'price': 'revenue'})
        .sort_values('purchase_month')
    )
    monthly['mom_growth_pct'] = monthly['revenue'].pct_change() * 100
    return monthly


# ===========================================================================
# 2. Product Metrics
# ===========================================================================

def calculate_product_metrics(sales: pd.DataFrame) -> pd.DataFrame:
    """
    Revenue breakdown by product category with market share percentage.

    Parameters
    ----------
    sales : pd.DataFrame
        Must contain 'product_category_name' and 'price'.

    Returns
    -------
    pd.DataFrame with columns:
        product_category_name, revenue, market_share_pct
        sorted descending by revenue.
    """
    cat = (
        sales.groupby('product_category_name')['price']
        .sum()
        .reset_index()
        .rename(columns={'price': 'revenue'})
        .sort_values('revenue', ascending=False)
    )
    cat['market_share_pct'] = (cat['revenue'] / cat['revenue'].sum() * 100).round(2)
    return cat.reset_index(drop=True)


# ===========================================================================
# 3. Geographic Metrics
# ===========================================================================

def calculate_geographic_metrics(sales: pd.DataFrame) -> pd.DataFrame:
    """
    Revenue, order count, and average order value by US state.

    Parameters
    ----------
    sales : pd.DataFrame
        Must contain 'customer_state', 'order_id', and 'price'.

    Returns
    -------
    pd.DataFrame with columns:
        customer_state, revenue, order_count, aov
        sorted descending by revenue.
    """
    geo = (
        sales.groupby('customer_state')
        .agg(
            revenue=('price', 'sum'),
            order_count=('order_id', 'nunique'),
        )
        .reset_index()
    )
    geo['aov'] = (geo['revenue'] / geo['order_count']).round(2)
    return geo.sort_values('revenue', ascending=False).reset_index(drop=True)


# ===========================================================================
# 4. Customer Experience Metrics
# ===========================================================================

def calculate_delivery_metrics(sales: pd.DataFrame) -> dict:
    """
    Summarise delivery speed and satisfaction scores.

    Parameters
    ----------
    sales : pd.DataFrame
        Must contain 'delivery_days' and 'review_score' columns.
        Deduplicate to one row per order before passing in if needed.

    Returns
    -------
    dict with keys:
        avg_delivery_days,
        avg_review_score,
        delivery_bucket_summary  (pd.DataFrame: delivery_time, avg_review_score, order_count)
    """
    order_level = sales[['order_id', 'delivery_days', 'review_score']].drop_duplicates('order_id')

    avg_days  = order_level['delivery_days'].mean()
    avg_score = order_level['review_score'].mean()

    order_level = order_level.copy()
    order_level['delivery_time'] = order_level['delivery_days'].apply(_bucket_delivery)

    bucket_summary = (
        order_level.groupby('delivery_time')
        .agg(
            avg_review_score=('review_score', 'mean'),
            order_count=('order_id', 'count'),
        )
        .reset_index()
    )
    # Ensure logical sort order
    bucket_order = ['1-3 days', '4-7 days', '8+ days']
    bucket_summary['delivery_time'] = pd.Categorical(
        bucket_summary['delivery_time'], categories=bucket_order, ordered=True
    )
    bucket_summary = bucket_summary.sort_values('delivery_time').reset_index(drop=True)

    return {
        'avg_delivery_days':   round(avg_days, 1),
        'avg_review_score':    round(avg_score, 2),
        'delivery_bucket_summary': bucket_summary,
    }


def _bucket_delivery(days: float) -> str:
    """Categorise delivery duration into three speed buckets."""
    if pd.isna(days):
        return 'unknown'
    if days <= 3:
        return '1-3 days'
    if days <= 7:
        return '4-7 days'
    return '8+ days'


def calculate_review_distribution(sales: pd.DataFrame) -> pd.DataFrame:
    """
    Proportion of orders at each review score (1-5).

    Parameters
    ----------
    sales : pd.DataFrame
        Must contain 'order_id' and 'review_score'.

    Returns
    -------
    pd.DataFrame with columns: review_score, proportion (0-1), pct
    """
    order_level = sales[['order_id', 'review_score']].drop_duplicates('order_id')
    dist = (
        order_level['review_score']
        .value_counts(normalize=True)
        .reset_index()
        .rename(columns={'proportion': 'proportion'})
        .sort_values('review_score')
    )
    dist['pct'] = (dist['proportion'] * 100).round(1)
    return dist


# ===========================================================================
# Visualisations
# ===========================================================================

def plot_revenue_trend(
    current_sales: pd.DataFrame,
    comparison_sales: pd.DataFrame,
    current_year: int,
    comparison_year: int,
) -> plt.Figure:
    """
    Line chart of monthly revenue for the current year vs the comparison year.

    Returns
    -------
    matplotlib.figure.Figure
    """
    cur  = calculate_monthly_revenue(current_sales)
    comp = calculate_monthly_revenue(comparison_sales)

    months = range(1, 13)
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_WIDE)

    ax.plot(cur['purchase_month'],  cur['revenue'],  marker='o', color=PRIMARY_COLOR,
            linewidth=2, markersize=5, label=str(current_year))
    ax.plot(comp['purchase_month'], comp['revenue'], marker='s', color=SECONDARY_COLOR,
            linewidth=2, markersize=5, linestyle='--', label=str(comparison_year))

    ax.set_xticks(list(months))
    ax.set_xticklabels(month_labels)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v/1e3:.0f}K'))
    ax.legend(title='Year', frameon=False)

    _apply_base_style(
        ax,
        title=f'Monthly Revenue Trend: {current_year} vs {comparison_year}',
        xlabel='Month',
        ylabel='Revenue (USD)',
    )
    fig.tight_layout()
    return fig


def plot_mom_growth(current_sales: pd.DataFrame, current_year: int) -> plt.Figure:
    """
    Bar chart of month-over-month revenue growth rate (%) for the current year.

    Returns
    -------
    matplotlib.figure.Figure
    """
    monthly = calculate_monthly_revenue(current_sales).dropna(subset=['mom_growth_pct'])

    colors = [POS_COLOR if v >= 0 else NEG_COLOR for v in monthly['mom_growth_pct']]
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    labels = [month_labels[int(m) - 1] for m in monthly['purchase_month']]

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_WIDE)
    ax.bar(labels, monthly['mom_growth_pct'], color=colors, width=0.6)
    ax.axhline(0, color='black', linewidth=0.8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.1f}%'))

    _apply_base_style(
        ax,
        title=f'Month-over-Month Revenue Growth Rate ({current_year})',
        xlabel='Month',
        ylabel='Growth Rate (%)',
    )
    fig.tight_layout()
    return fig


def plot_category_performance(product_metrics: pd.DataFrame, current_year: int) -> plt.Figure:
    """
    Horizontal bar chart of revenue by product category.

    Parameters
    ----------
    product_metrics : pd.DataFrame
        Output of calculate_product_metrics().

    Returns
    -------
    matplotlib.figure.Figure
    """
    df = product_metrics.sort_values('revenue')

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_SQ)
    bars = ax.barh(df['product_category_name'], df['revenue'], color=PRIMARY_COLOR, height=0.6)

    # Annotate with market share
    for bar, share in zip(bars, df['market_share_pct']):
        ax.text(
            bar.get_width() + bar.get_width() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f'{share:.1f}%',
            va='center', fontsize=9, color='#444',
        )

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v/1e3:.0f}K'))

    _apply_base_style(
        ax,
        title=f'Revenue by Product Category ({current_year})',
        xlabel='Total Revenue (USD)',
        ylabel='Product Category',
    )
    fig.tight_layout()
    return fig


def plot_geographic_performance(geo_metrics: pd.DataFrame, current_year: int):
    """
    Interactive choropleth map of revenue by US state using Plotly.

    Parameters
    ----------
    geo_metrics : pd.DataFrame
        Output of calculate_geographic_metrics().

    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = px.choropleth(
        geo_metrics,
        locations='customer_state',
        color='revenue',
        locationmode='USA-states',
        scope='usa',
        color_continuous_scale='Blues',
        labels={'revenue': 'Revenue (USD)', 'customer_state': 'State'},
        title=f'Revenue by State ({current_year})',
        hover_data={'order_count': True, 'aov': ':.2f'},
    )
    fig.update_layout(
        coloraxis_colorbar=dict(
            title='Revenue',
            tickformat='$,.0f',
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def plot_review_distribution(review_dist: pd.DataFrame, current_year: int) -> plt.Figure:
    """
    Horizontal bar chart of review score proportions.

    Parameters
    ----------
    review_dist : pd.DataFrame
        Output of calculate_review_distribution().

    Returns
    -------
    matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [PRIMARY_COLOR if s == 5 else SECONDARY_COLOR if s == 4
              else ACCENT_COLOR if s == 3 else NEG_COLOR
              for s in review_dist['review_score']]

    ax.barh(
        review_dist['review_score'].astype(str),
        review_dist['proportion'],
        color=colors,
        height=0.6,
    )
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v*100:.0f}%'))

    for i, (val, pct) in enumerate(zip(review_dist['proportion'], review_dist['pct'])):
        ax.text(val + 0.005, i, f'{pct}%', va='center', fontsize=9)

    _apply_base_style(
        ax,
        title=f'Review Score Distribution ({current_year})',
        xlabel='Proportion of Orders',
        ylabel='Review Score',
    )
    fig.tight_layout()
    return fig


def plot_delivery_vs_score(delivery_metrics: dict, current_year: int) -> plt.Figure:
    """
    Bar chart comparing average review score across delivery speed buckets.

    Parameters
    ----------
    delivery_metrics : dict
        Output of calculate_delivery_metrics().

    Returns
    -------
    matplotlib.figure.Figure
    """
    df = delivery_metrics['delivery_bucket_summary']

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(df['delivery_time'], df['avg_review_score'], color=PRIMARY_COLOR, width=0.4)

    ax.set_ylim(
        df['avg_review_score'].min() * 0.97,
        df['avg_review_score'].max() * 1.03,
    )

    for i, (score, count) in enumerate(zip(df['avg_review_score'], df['order_count'])):
        ax.text(i, score + 0.002, f'{score:.2f}\n(n={count})',
                ha='center', va='bottom', fontsize=9)

    _apply_base_style(
        ax,
        title=f'Average Review Score by Delivery Speed ({current_year})',
        xlabel='Delivery Speed',
        ylabel='Average Review Score (1-5)',
    )
    fig.tight_layout()
    return fig


# ===========================================================================
# Summary printer
# ===========================================================================

def print_metrics_summary(revenue_metrics: dict, delivery_metrics: dict) -> None:
    """
    Print a formatted console summary of key business metrics.

    Parameters
    ----------
    revenue_metrics : dict
        Output of calculate_revenue_metrics().
    delivery_metrics : dict
        Output of calculate_delivery_metrics().
    """
    cy = revenue_metrics['current_year']
    py = revenue_metrics['comparison_year']

    print(f"BUSINESS METRICS SUMMARY - {cy}")
    print("=" * 60)

    print("\nREVENUE PERFORMANCE")
    print(f"  Total Revenue ({cy}):        ${revenue_metrics[f'total_revenue_{cy}']:>12,.2f}")
    print(f"  Total Revenue ({py}):        ${revenue_metrics[f'total_revenue_{py}']:>12,.2f}")
    print(f"  YoY Revenue Growth:          {revenue_metrics['revenue_growth_pct']:>+11.2f}%")

    print("\nORDERS")
    print(f"  Total Orders ({cy}):         {revenue_metrics[f'total_orders_{cy}']:>12,}")
    print(f"  Total Orders ({py}):         {revenue_metrics[f'total_orders_{py}']:>12,}")
    print(f"  YoY Order Growth:            {revenue_metrics['order_growth_pct']:>+11.2f}%")

    print("\nAVERAGE ORDER VALUE")
    print(f"  AOV ({cy}):                  ${revenue_metrics[f'aov_{cy}']:>12,.2f}")
    print(f"  AOV ({py}):                  ${revenue_metrics[f'aov_{py}']:>12,.2f}")
    print(f"  YoY AOV Growth:              {revenue_metrics['aov_growth_pct']:>+11.2f}%")

    print("\nCUSTOMER EXPERIENCE")
    print(f"  Average Review Score:        {delivery_metrics['avg_review_score']:>12.2f} / 5.0")
    print(f"  Average Delivery Time:       {delivery_metrics['avg_delivery_days']:>11.1f} days")
    print("=" * 60)
