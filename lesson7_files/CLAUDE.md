# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Virtual Environment

```bash
# Activate before any work
source .venv/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Deactivate when done — always run this after finishing any processing session
deactivate
```

Always activate the venv before running notebooks, scripts, or installing packages. Always call `deactivate` when processing is complete to close the environment.

## Running the Notebook

```bash
source .venv/bin/activate
jupyter notebook EDA.ipynb
deactivate
```

## Data: `ecommerce_data/`

Six CSV files make up the dataset:

| File | Key columns |
|------|-------------|
| `orders_dataset.csv` | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_delivered_customer_date` |
| `order_items_dataset.csv` | `order_id`, `product_id`, `seller_id`, `price`, `freight_value` |
| `products_dataset.csv` | `product_id`, `product_category_name` (13 categories) |
| `customers_dataset.csv` | `customer_id`, `customer_unique_id`, `customer_city`, `customer_state` |
| `order_reviews_dataset.csv` | `review_id`, `order_id`, `review_score` (1–5) |
| `order_payments_dataset.csv` | `order_id`, payment details |

Order statuses: `delivered`, `shipped`, `canceled`, `processing`, `pending`, `returned`. Most analyses filter to `delivered` only (~93.6% of 2023 orders).

## Notebook: `EDA.ipynb`

The notebook answers four business questions for 2023 vs 2022, all working from a `sales_delivered` DataFrame (merged `order_items` + `orders`, filtered to `status == 'delivered'`):

1. **Revenue comparison** — total 2023 revenue ($3.36M), YoY growth (−2.46%)
2. **Month-over-month growth** — `pct_change()` on monthly grouped revenue; avg MoM growth −0.39%
3. **Top product categories** — merge with `products` on `product_id`, group by `product_category_name`
4. **Sales by state** — chain merge: `sales_delivered_2023 → orders → customers`, group by `customer_state`, visualized as a Plotly USA choropleth

Additional metrics computed: average order value ($724.98), total orders (4,635), delivery speed (avg 8 days), review score by delivery bucket (`1-3 days`, `4-7 days`, `8+ days`), overall avg review score (4.10/5).

**Known warnings**: The notebook uses chained assignment on `sales_delivered` slices, triggering `SettingWithCopyWarning`. Use `.loc[]` or reassign with `.copy()` when modifying columns on filtered DataFrames.
