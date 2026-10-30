"""
MarketSphere synthetic marketplace data generator.

Creates:
  data/clean/*.csv and order_events.jsonl
  data/raw/*.csv and order_events.jsonl
  data/raw/customer_updates.jsonl

Default scale: 50k customers, 1k sellers, 5k products, 100k orders.
The raw layer intentionally contains data-quality defects. Do not enforce
PK/FK constraints on the raw files; validate and quarantine them downstream.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2025-12-31 23:59:59")
CITIES = ["Kuala Lumpur", "Petaling Jaya", "Shah Alam", "Johor Bahru",
          "George Town", "Ipoh", "Kuching", "Kota Kinabalu", "Malacca"]
CATEGORIES = ["Electronics", "Fashion", "Home & Living", "Beauty",
              "Sports", "Books", "Toys", "Grocery"]
BRANDS = ["Northstar", "UrbanNest", "NovaTech", "Everyday Co", "Peak",
          "Luma", "BrightLeaf", "Mosaic"]
ORDER_STATUSES = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled", "Returned"]
PAYMENT_METHODS = ["Credit Card", "Debit Card", "E-Wallet", "Bank Transfer", "Cash on Delivery"]
CARRIERS = ["Pos Malaysia", "J&T Express", "DHL", "Ninja Van", "Flash Express"]

def timestamp_series(n: int) -> pd.Series:
    seconds = np.random.randint(0, int((END - START).total_seconds()), size=n)
    return START + pd.to_timedelta(seconds, unit="s")

def make_id(prefix: str, n: int, width: int = 6) -> list[str]:
    return [f"{prefix}{i:0{width}d}" for i in range(1, n + 1)]

def save_csv(df: pd.DataFrame, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(folder / f"{name}.csv", index=False)

def build_clean_data(out: Path, orders_n: int) -> dict[str, pd.DataFrame]:
    fake = Faker("en_US")
    Faker.seed(SEED)
    np.random.seed(SEED)
    random.seed(SEED)

    n_customers = max(1000, int(orders_n * 0.50))
    n_sellers = max(100, int(orders_n * 0.01))
    n_products = max(500, int(orders_n * 0.05))

    customer_ids = make_id("CUS", n_customers)
    seller_ids = make_id("SEL", n_sellers)
    product_ids = make_id("PRD", n_products)
    order_ids = make_id("ORD", orders_n)

    customers = pd.DataFrame({
        "customer_id": customer_ids,
        "first_name": [fake.first_name() for _ in range(n_customers)],
        "last_name": [fake.last_name() for _ in range(n_customers)],
        "email": [f"customer{i:06d}@example.test" for i in range(1, n_customers + 1)],
        "phone": [fake.numerify(text="01########") for _ in range(n_customers)],
        "city": np.random.choice(CITIES, n_customers),
        "state": np.random.choice(["Selangor", "Kuala Lumpur", "Johor", "Penang",
                                   "Perak", "Sarawak", "Sabah", "Melaka"], n_customers),
        "country": "Malaysia",
        "postal_code": [fake.postcode() for _ in range(n_customers)],
        "registration_date": pd.to_datetime(timestamp_series(n_customers)).date.astype(str),
        "customer_segment": np.random.choice(["New", "Regular", "Loyal", "VIP"],
                                             n_customers, p=[.25, .40, .25, .10]),
        "is_active": np.random.choice([True, False], n_customers, p=[.92, .08])
    })

    sellers = pd.DataFrame({
        "seller_id": seller_ids,
        "seller_name": [fake.company() for _ in range(n_sellers)],
        "email": [f"seller{i:05d}@example.test" for i in range(1, n_sellers + 1)],
        "city": np.random.choice(CITIES, n_sellers),
        "country": "Malaysia",
        "registration_date": pd.to_datetime(timestamp_series(n_sellers)).date.astype(str),
        "seller_rating": np.round(np.random.uniform(3.0, 5.0, n_sellers), 2),
        "seller_status": np.random.choice(["Active", "Inactive", "Suspended"],
                                          n_sellers, p=[.88, .09, .03])
    })

    products = pd.DataFrame({
        "product_id": product_ids,
        "product_name": [f"{random.choice(BRANDS)} {fake.word().title()} {random.choice(['Pro', 'Plus', 'Classic', 'Mini', 'Max'])}"
                         for _ in range(n_products)],
        "category": np.random.choice(CATEGORIES, n_products),
        "brand": np.random.choice(BRANDS, n_products),
        "unit_price": np.round(np.random.lognormal(mean=3.7, sigma=.8, size=n_products), 2),
        "cost_price": 0.0,
        "weight_grams": np.random.randint(50, 15000, n_products),
        "is_active": np.random.choice([True, False], n_products, p=[.94, .06])
    })
    products["cost_price"] = np.round(products["unit_price"] * np.random.uniform(.45, .80, n_products), 2)

    order_dates = timestamp_series(orders_n)
    orders = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": np.random.choice(customer_ids, orders_n),
        "order_date": order_dates,
        "order_status": np.random.choice(ORDER_STATUSES, orders_n,
                                         p=[.05, .10, .12, .60, .08, .05]),
        "shipping_method": np.random.choice(["Standard", "Express", "Same Day"], orders_n,
                                            p=[.65, .28, .07]),
        "currency": "MYR",
        "order_total": 0.0
    })

    item_rows = []
    product_price = products.set_index("product_id")["unit_price"].to_dict()
    item_counter = 1
    for oid in order_ids:
        count = int(np.random.choice([1, 2, 3, 4, 5], p=[.30, .30, .22, .13, .05]))
        chosen_products = np.random.choice(product_ids, count, replace=False)
        for pid in chosen_products:
            price = float(product_price[pid])
            seller = random.choice(seller_ids)
            qty = int(np.random.choice([1, 2, 3, 4], p=[.65, .23, .09, .03]))
            discount = round(price * qty * random.choice([0, 0, 0, .05, .10, .15]), 2)
            line_total = round(qty * price - discount, 2)
            item_rows.append((f"ITM{item_counter:08d}", oid, pid, seller, qty,
                              price, discount, line_total))
            item_counter += 1
    order_items = pd.DataFrame(item_rows, columns=[
        "order_item_id", "order_id", "product_id", "seller_id", "quantity",
        "unit_price", "discount_amount", "line_total"
    ])
    totals = order_items.groupby("order_id")["line_total"].sum()
    orders["order_total"] = orders["order_id"].map(totals).round(2)

    payment_rows = []
    payment_counter = 1
    for row in orders.itertuples(index=False):
        # One or occasionally two payment attempts; successful payment amount is not guaranteed.
        attempts = 2 if random.random() < .08 else 1
        remaining = float(row.order_total)
        for attempt in range(attempts):
            status = "Successful" if attempt == attempts - 1 else "Failed"
            amount = remaining if status == "Successful" else round(remaining * .30, 2)
            payment_rows.append((f"PAY{payment_counter:08d}", row.order_id,
                                 row.order_date + pd.Timedelta(minutes=random.randint(1, 90)),
                                 random.choice(PAYMENT_METHODS), amount, status))
            payment_counter += 1

    payments = pd.DataFrame(payment_rows, columns=[
        "payment_id", "order_id", "payment_date", "payment_method",
        "payment_amount", "payment_status"
    ])

    shipment_rows = []
    shipment_counter = 1
    for row in orders.itertuples(index=False):
        if row.order_status in ("Cancelled", "Pending"):
            continue
        shipped = row.order_date + pd.Timedelta(days=random.randint(1, 3))
        delivered = shipped + pd.Timedelta(days=random.randint(1, 9)) if row.order_status == "Delivered" else pd.NaT
        shipment_rows.append((f"SHP{shipment_counter:08d}", row.order_id, shipped,
                              delivered, random.choice(CARRIERS),
                              "Delivered" if pd.notna(delivered) else "In Transit",
                              round(random.uniform(5, 35), 2)))
        shipment_counter += 1
    shipments = pd.DataFrame(shipment_rows, columns=[
        "shipment_id", "order_id", "shipped_at", "delivered_at",
        "carrier", "shipment_status", "shipping_cost"
    ])

    movement_rows = []
    movement_counter = 1
    for row in order_items.itertuples(index=False):
        movement_rows.append((f"MOV{movement_counter:09d}", row.product_id, row.seller_id,
                              order_dates[int(row.order_id[3:]) - 1],
                              "SALE", -int(row.quantity), random.randint(0, 500)))
        movement_counter += 1
    # Add independent replenishment and adjustment records.
    extra_n = max(10000, len(order_items) // 2)
    for _ in range(extra_n):
        pid = random.choice(product_ids)
        sid = random.choice(seller_ids)
        typ = random.choice(["RESTOCK", "RETURN", "ADJUSTMENT"])
        qty = random.randint(1, 100) * (1 if typ != "ADJUSTMENT" or random.random() > .2 else -1)
        movement_rows.append((f"MOV{movement_counter:09d}", pid, sid,
                              random.choice(timestamp_series(1)).to_pydatetime(),
                              typ, qty, random.randint(0, 1000)))
        movement_counter += 1
    inventory = pd.DataFrame(movement_rows, columns=[
        "movement_id", "product_id", "seller_id", "movement_date",
        "movement_type", "quantity_change", "stock_after"
    ])

    clean = {
        "customers": customers, "sellers": sellers, "products": products,
        "orders": orders, "order_items": order_items, "payments": payments,
        "shipments": shipments, "inventory_movements": inventory
    }

    clean_dir = out / "data" / "clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    for name, df in clean.items():
        save_csv(df, clean_dir, name)

    # Three lifecycle events per order. Ingestion time can be later than event time.
    event_path = clean_dir / "order_events.jsonl"
    with event_path.open("w", encoding="utf-8") as f:
        for row in orders.itertuples(index=False):
            for event_type, offset in [("ORDER_CREATED", 0), ("ORDER_CONFIRMED", 30),
                                       ("ORDER_STATUS_UPDATED", 60)]:
                event_ts = row.order_date + pd.Timedelta(minutes=offset)
                ingested = event_ts + pd.Timedelta(minutes=random.randint(1, 20))
                event = {
                    "event_id": f"EVT{random.getrandbits(48):012d}",
                    "order_id": row.order_id,
                    "event_type": event_type,
                    "event_timestamp": event_ts.isoformat(),
                    "ingested_at": ingested.isoformat(),
                    "source_system": random.choice(["marketplace_app", "order_service", "seller_portal"]),
                    "event_version": 1,
                    "metadata": {
                        "customer_id": row.customer_id,
                        "order_status": row.order_status,
                        "order_total": float(row.order_total),
                        "currency": row.currency
                    }
                }
                f.write(json.dumps(event) + "\n")
    return clean

def corrupt_data(clean: dict[str, pd.DataFrame], out: Path) -> None:
    rng = np.random.default_rng(SEED + 100)
    raw_dir = out / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = {name: df.copy(deep=True) for name, df in clean.items()}

    def choose_indices(df, fraction):
        n = max(1, int(len(df) * fraction))
        return rng.choice(df.index.to_numpy(), size=min(n, len(df)), replace=False)

    # Missing values, inconsistent text and malformed fields.
    idx = choose_indices(raw["customers"], .012)
    raw["customers"].loc[idx, "email"] = None
    idx = choose_indices(raw["customers"], .004)
    raw["customers"].loc[idx, "email"] = "not-an-email"
    idx = choose_indices(raw["customers"], .008)
    raw["customers"].loc[idx, "city"] = raw["customers"].loc[idx, "city"].str.upper()
    idx = choose_indices(raw["customers"], .003)
    raw["customers"].loc[idx, "phone"] = None

    idx = choose_indices(raw["products"], .004)
    raw["products"].loc[idx, "unit_price"] = -abs(raw["products"].loc[idx, "unit_price"])
    idx = choose_indices(raw["products"], .002)
    raw["products"].loc[idx, "category"] = "Unknown_Category"
    idx = choose_indices(raw["products"], .001)
    raw["products"].loc[idx, "unit_price"] = 999999.99

    idx = choose_indices(raw["orders"], .006)
    raw["orders"].loc[idx, "customer_id"] = "CUS999999"
    idx = choose_indices(raw["orders"], .005)
    raw["orders"].loc[idx, "order_status"] = raw["orders"].loc[idx, "order_status"].str.upper()
    idx = choose_indices(raw["orders"], .002)
    raw["orders"].loc[idx, "order_total"] = -abs(raw["orders"].loc[idx, "order_total"])
    idx = choose_indices(raw["orders"], .001)
    raw["orders"].loc[idx, "order_date"] = pd.Timestamp("2035-01-01")

    idx = choose_indices(raw["order_items"], .004)
    raw["order_items"].loc[idx, "quantity"] = -abs(raw["order_items"].loc[idx, "quantity"])
    idx = choose_indices(raw["order_items"], .003)
    raw["order_items"].loc[idx, "product_id"] = "PRD999999"
    idx = choose_indices(raw["order_items"], .002)
    raw["order_items"].loc[idx, "unit_price"] = "PRICE_ERROR"
    # Repeated primary keys.
    raw["orders"] = pd.concat([raw["orders"], raw["orders"].sample(frac=.001, random_state=SEED)], ignore_index=True)
    raw["customers"] = pd.concat([raw["customers"], raw["customers"].sample(frac=.001, random_state=SEED)], ignore_index=True)

    idx = choose_indices(raw["payments"], .003)
    raw["payments"].loc[idx, "payment_amount"] = -abs(raw["payments"].loc[idx, "payment_amount"])
    idx = choose_indices(raw["payments"], .002)
    raw["payments"].loc[idx, "payment_status"] = "unknown_status"
    # A small number of amounts become strings to simulate source type drift.
    idx = choose_indices(raw["payments"], .001)
    raw["payments"]["payment_amount"] = raw["payments"]["payment_amount"].astype(object)
    raw["payments"].loc[idx, "payment_amount"] = "AMOUNT_PENDING"

    idx = choose_indices(raw["shipments"], .003)
    raw["shipments"].loc[idx, "delivered_at"] = pd.Timestamp("2023-01-01")
    idx = choose_indices(raw["shipments"], .002)
    raw["shipments"].loc[idx, "carrier"] = None

    idx = choose_indices(raw["inventory_movements"], .002)
    raw["inventory_movements"].loc[idx, "stock_after"] = -999

    for name, df in raw.items():
        save_csv(df, raw_dir, name)

    # Corrupt and evolve JSON events: late arrivals, duplicate IDs, schema drift,
    # conflicting event versions and malformed JSON lines.
    clean_events = out / "data" / "clean" / "order_events.jsonl"
    lines = clean_events.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    for event in events[::500]:
        event["ingested_at"] = (pd.Timestamp(event["event_timestamp"]) + pd.Timedelta(days=2)).isoformat()
    for event in events[::1000]:
        event["event_version"] = 2
        event["metadata"]["source_note"] = "updated_by_order_service"
    if events:
        events.extend(events[:max(1, len(events)//1000)])  # duplicate events
    # Schema drift on a subset: additional attribute appears in newer records.
    for event in events[::200]:
        event["schema_version"] = 2
        event["metadata"]["customer_tier"] = random.choice(["Silver", "Gold", "Platinum"])
    with (raw_dir / "order_events.jsonl").open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
        f.write('{"event_id":"EVT_BROKEN","order_id":"ORD000001","metadata": \n')

    # Conflicting customer updates as a separate JSONL change feed.
    updates_path = raw_dir / "customer_updates.jsonl"
    sample = clean["customers"].sample(n=min(500, len(clean["customers"])), random_state=SEED)
    with updates_path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(sample.itertuples(index=False), start=1):
            version = 2 if i % 2 == 0 else 1
            record = {
                "customer_id": row.customer_id,
                "email": f"updated_{row.customer_id.lower()}@example.test" if version == 2 else row.email,
                "record_version": version,
                "updated_at": (pd.Timestamp("2025-12-01") + pd.Timedelta(minutes=i)).isoformat(),
                "source_system": "crm"
            }
            f.write(json.dumps(record) + "\n")
        f.write(json.dumps({
            "customer_id": "CUS000001",
            "email": "conflicting_update@example.test",
            "record_version": 3,
            "updated_at": "2025-12-20T12:00:00",
            "source_system": "crm"
        }) + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", type=int, default=100_000,
                        help="Number of orders to generate (default: 100000)")
    parser.add_argument("--output", type=str, default=".",
                        help="Project output directory")
    args = parser.parse_args()
    if args.orders < 100:
        raise ValueError("Use at least 100 orders.")
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    print(f"Generating {args.orders:,} orders...")
    clean = build_clean_data(out, args.orders)
    print("Creating production-like raw data with intentional quality issues...")
    corrupt_data(clean, out)
    print("\nGeneration complete.")
    print(f"Clean data: {out / 'data' / 'clean'}")
    print(f"Raw data:   {out / 'data' / 'raw'}")
    for name, df in clean.items():
        print(f"{name:22s} {len(df):>10,} rows")

if __name__ == "__main__":
    main()
