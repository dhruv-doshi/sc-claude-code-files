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

## Running the Notebooks

```bash
source .venv/bin/activate
jupyter notebook EDA_Refactored.ipynb   # refactored, modular version (preferred)
jupyter notebook EDA.ipynb              # original single-file analysis
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

## Module Architecture

Three Python files work together:

| File | Role |
|---|---|
| `data_loader.py` | `EcommerceDataLoader` — loads all 6 CSVs, merges them, parses datetimes, computes `delivery_days`/`purchase_year`/`purchase_month`. Use `create_sales_dataset(year_filter, month_filter, status_filter)` to get a filtered working dataset. |
| `business_metrics.py` | Pure calculation functions (`calculate_revenue_metrics`, `calculate_product_metrics`, `calculate_geographic_metrics`, `calculate_delivery_metrics`, `calculate_review_distribution`) plus matching `plot_*` functions for each. No side effects — all functions return DataFrames, dicts, or figures. |
| `EDA_Refactored.ipynb` | Calls the two modules above. All analysis parameters (`ANALYSIS_YEAR`, `COMPARISON_YEAR`, `ANALYSIS_MONTH`, `ORDER_STATUS`) live in a single config cell at the top. |

## Notebook: `EDA.ipynb`

Original single-file notebook. Answers four business questions for 2023 vs 2022 using inline pandas merges and plots. Kept for reference. Known issue: uses chained assignment on filtered slices, producing `SettingWithCopyWarning`.
