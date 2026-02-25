# E-commerce Business Analytics

Exploratory data analysis of an e-commerce platform, structured as a modular, configurable framework. The analysis covers revenue performance, product category mix, geographic distribution, and customer experience for any chosen time period.

---

## Project Structure

```
lesson7_files/
├── dashboard.py             # Streamlit analytics dashboard
├── EDA_Refactored.ipynb     # Main analysis notebook
├── EDA.ipynb                # Original single-file notebook (reference only)
├── data_loader.py           # Data loading, merging, and preprocessing
├── business_metrics.py      # Metric calculations and visualisations
├── requirements.txt         # Python dependencies
├── ecommerce_data/          # Source CSV files
│   ├── orders_dataset.csv
│   ├── order_items_dataset.csv
│   ├── products_dataset.csv
│   ├── customers_dataset.csv
│   ├── order_reviews_dataset.csv
│   └── order_payments_dataset.csv
```

---

## Setup

**Requirements:** Python 3.8 or higher.

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Dashboard

```bash
source .venv/bin/activate
streamlit run dashboard.py
```

The dashboard opens in your browser at `http://localhost:8501`. Use the **Date Range** filter in the top-right to restrict the analysis period; all KPIs and charts update automatically. The comparison period is the same date window shifted back by one year.

---

## Running the Analysis (Notebook)

```bash
source .venv/bin/activate
jupyter notebook EDA_Refactored.ipynb
```

Open `EDA_Refactored.ipynb` and locate the configuration cell near the top:

```python
DATA_PATH       = 'ecommerce_data/'   # path to the CSV directory
ANALYSIS_YEAR   = 2023                # year to analyse
COMPARISON_YEAR = 2022                # year used for year-over-year comparison
ANALYSIS_MONTH  = None                # set to 1-12 for a single month; None for full year
ORDER_STATUS    = 'delivered'         # order status filter applied to all metrics
```

Adjust these values, then run all cells. Every metric and chart updates automatically.

---

## Business Questions Answered

| Section | Question |
|---|---|
| Revenue Performance | How did total revenue, order volume, and average order value compare year-over-year? |
| Revenue Performance | What is the month-over-month revenue growth trend within the analysis year? |
| Product Category Analysis | Which product categories generate the most revenue and what share of total do they represent? |
| Geographic Performance | Which US states drive the most revenue and how does average order value vary by region? |
| Customer Experience | How does delivery speed relate to customer satisfaction (review scores)? |

---

## Module Reference

### `data_loader.py`

Handles all data ingestion and preprocessing. Import via:

```python
from data_loader import load_and_process_data, EcommerceDataLoader

# Load and process all data in one call
loader, processed = load_and_process_data('ecommerce_data/')

# Create a filtered dataset for a specific period
sales_2023 = loader.create_sales_dataset(
    year_filter=2023,
    month_filter=None,       # or 1-12
    status_filter='delivered'
)
```

`create_sales_dataset` returns a flat DataFrame with all tables merged and derived columns added (`delivery_days`, `purchase_year`, `purchase_month`).

---

### `business_metrics.py`

All calculation and visualisation functions. Each function accepts a plain DataFrame, so they can be used independently of `data_loader`.

**Calculation functions** — return a dict or DataFrame:

| Function | Returns |
|---|---|
| `calculate_revenue_metrics(current, comparison, cur_year, cmp_year)` | Dict of KPIs: total revenue, order count, AOV with YoY growth for each |
| `calculate_monthly_revenue(sales)` | DataFrame: month, revenue, MoM growth % |
| `calculate_product_metrics(sales)` | DataFrame: category, revenue, market share % |
| `calculate_geographic_metrics(sales)` | DataFrame: state, revenue, order count, AOV |
| `calculate_delivery_metrics(sales)` | Dict: avg delivery days, avg review score, bucket summary |
| `calculate_review_distribution(sales)` | DataFrame: review score, proportion, pct |

**Visualisation functions** — return a figure object:

| Function | Chart type |
|---|---|
| `plot_revenue_trend(...)` | Line chart: monthly revenue, current vs comparison year |
| `plot_mom_growth(...)` | Bar chart: month-over-month growth rate |
| `plot_category_performance(...)` | Horizontal bar chart: revenue by category with market share labels |
| `plot_geographic_performance(...)` | Interactive Plotly choropleth: revenue by US state |
| `plot_review_distribution(...)` | Horizontal bar chart: proportion of orders per review score |
| `plot_delivery_vs_score(...)` | Bar chart: average review score by delivery speed bucket |

**Summary printer:**

```python
from business_metrics import print_metrics_summary
print_metrics_summary(revenue_metrics, delivery_metrics)
```

---

## Dashboard Layout

| Section | Contents |
|---|---|
| **Header** | Title (left) + Date Range filter (right, applies globally) |
| **KPI Row** | Total Revenue · Monthly Growth · Avg Order Value · Total Orders — each with a YoY trend indicator (green = positive, red = negative) |
| **Charts — row 1** | Monthly revenue trend (solid = current year, dashed = prior year) · Top 10 revenue categories (blue gradient bar chart) |
| **Charts — row 2** | Revenue by US state choropleth · Avg review score by delivery-time bucket |
| **Bottom Row** | Avg Delivery Time (with trend) · Review Score (large number + stars) |

---

## Extending the Analysis

- **New metric:** add a `calculate_*` function to `business_metrics.py` and a corresponding `plot_*` function, then call them in a new notebook section.
- **New data source:** extend `EcommerceDataLoader.process_data()` in `data_loader.py` to merge the additional table; derived columns remain in one place.
- **Different time granularity:** pass a specific `month_filter` to `create_sales_dataset` and adjust `ANALYSIS_MONTH` in the notebook config cell.
