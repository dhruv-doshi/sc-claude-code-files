"""
data_loader.py
--------------
Handles all data loading, merging, and preprocessing for the e-commerce dataset.

Usage
-----
    from data_loader import EcommerceDataLoader, load_and_process_data

    # Quick start
    loader, processed = load_and_process_data('ecommerce_data/')

    # Filtered dataset for analysis
    sales = loader.create_sales_dataset(year_filter=2023, status_filter='delivered')
"""

import os
import pandas as pd


class EcommerceDataLoader:
    """
    Loads and preprocesses the six e-commerce CSV files.

    Parameters
    ----------
    data_path : str
        Path to the directory containing the CSV files.
    """

    # Expected file names inside data_path
    FILES = {
        'orders':       'orders_dataset.csv',
        'order_items':  'order_items_dataset.csv',
        'products':     'products_dataset.csv',
        'customers':    'customers_dataset.csv',
        'reviews':      'order_reviews_dataset.csv',
        'payments':     'order_payments_dataset.csv',
    }

    # Datetime columns that need parsing per file
    DATETIME_COLS = {
        'orders': [
            'order_purchase_timestamp',
            'order_approved_at',
            'order_delivered_carrier_date',
            'order_delivered_customer_date',
            'order_estimated_delivery_date',
        ],
        'reviews': ['review_creation_date', 'review_answer_timestamp'],
        'order_items': ['shipping_limit_date'],
    }

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.raw: dict[str, pd.DataFrame] = {}
        self.processed: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_raw_data(self) -> dict[str, pd.DataFrame]:
        """
        Read all six CSV files into a dict keyed by table name.

        Returns
        -------
        dict of {str: pd.DataFrame}
        """
        for key, filename in self.FILES.items():
            filepath = os.path.join(self.data_path, filename)
            df = pd.read_csv(filepath)
            for col in self.DATETIME_COLS.get(key, []):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            self.raw[key] = df
        return self.raw

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process_data(self) -> pd.DataFrame:
        """
        Merge all tables into a single flat DataFrame and add derived columns.

        Derived columns added
        ---------------------
        - purchase_year   : int  year extracted from order_purchase_timestamp
        - purchase_month  : int  month extracted from order_purchase_timestamp
        - delivery_days   : int  calendar days from purchase to customer delivery

        Returns
        -------
        pd.DataFrame
            Fully merged and enriched dataset.
        """
        if not self.raw:
            self.load_raw_data()

        orders   = self.raw['orders']
        items    = self.raw['order_items']
        products = self.raw['products']
        customers = self.raw['customers']
        reviews  = self.raw['reviews']

        # Merge order items with order header
        df = items[['order_id', 'order_item_id', 'product_id', 'price', 'freight_value']].merge(
            orders[['order_id', 'customer_id', 'order_status',
                    'order_purchase_timestamp', 'order_delivered_customer_date']],
            on='order_id',
            how='left',
        )

        # Attach product category
        df = df.merge(
            products[['product_id', 'product_category_name']],
            on='product_id',
            how='left',
        )

        # Attach customer state
        df = df.merge(
            customers[['customer_id', 'customer_state', 'customer_city']],
            on='customer_id',
            how='left',
        )

        # Attach review score (one review per order; drop duplicates before merging)
        reviews_deduped = (
            reviews[['order_id', 'review_score']]
            .drop_duplicates(subset='order_id', keep='first')
        )
        df = df.merge(reviews_deduped, on='order_id', how='left')

        # Derived time columns
        df['purchase_year']  = df['order_purchase_timestamp'].dt.year
        df['purchase_month'] = df['order_purchase_timestamp'].dt.month

        # Delivery duration in calendar days
        df['delivery_days'] = (
            df['order_delivered_customer_date'] - df['order_purchase_timestamp']
        ).dt.days

        self.processed = df
        return df

    # ------------------------------------------------------------------
    # Filtered dataset
    # ------------------------------------------------------------------

    def create_sales_dataset(
        self,
        year_filter: int | None = None,
        month_filter: int | None = None,
        status_filter: str = 'delivered',
    ) -> pd.DataFrame:
        """
        Return a filtered slice of the processed dataset.

        Parameters
        ----------
        year_filter : int or None
            Keep only rows where purchase_year equals this value.
            Pass None to include all years.
        month_filter : int or None
            Keep only rows where purchase_month equals this value (1-12).
            Pass None to include all months.
        status_filter : str or None
            Keep only rows matching this order_status value.
            Pass None to include all statuses.

        Returns
        -------
        pd.DataFrame
        """
        if self.processed is None:
            self.process_data()

        df = self.processed.copy()

        if status_filter is not None:
            df = df[df['order_status'] == status_filter]
        if year_filter is not None:
            df = df[df['purchase_year'] == year_filter]
        if month_filter is not None:
            df = df[df['purchase_month'] == month_filter]

        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def orders(self) -> pd.DataFrame:
        """Raw orders table."""
        return self.raw.get('orders', pd.DataFrame())

    @property
    def products(self) -> pd.DataFrame:
        """Raw products table."""
        return self.raw.get('products', pd.DataFrame())

    @property
    def customers(self) -> pd.DataFrame:
        """Raw customers table."""
        return self.raw.get('customers', pd.DataFrame())

    @property
    def reviews(self) -> pd.DataFrame:
        """Raw reviews table."""
        return self.raw.get('reviews', pd.DataFrame())


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def load_and_process_data(data_path: str) -> tuple[EcommerceDataLoader, pd.DataFrame]:
    """
    Load and process all e-commerce data in one call.

    Parameters
    ----------
    data_path : str
        Directory containing the six CSV files.

    Returns
    -------
    loader : EcommerceDataLoader
        Initialised loader instance (raw tables accessible via loader.raw).
    processed : pd.DataFrame
        Fully merged and enriched dataset.

    Example
    -------
        loader, data = load_and_process_data('ecommerce_data/')
        sales_2023 = loader.create_sales_dataset(year_filter=2023)
    """
    loader = EcommerceDataLoader(data_path)
    processed = loader.process_data()
    return loader, processed
