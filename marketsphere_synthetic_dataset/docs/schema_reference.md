# MarketSphere schema reference

All identifiers are strings. Dates/timestamps are ISO-compatible. Monetary
values use decimal precision (2 decimal places) and currency is MYR.

| Table | Primary key | Foreign keys |
|---|---|---|
| customers | customer_id | — |
| sellers | seller_id | — |
| products | product_id | — |
| orders | order_id | customer_id -> customers.customer_id |
| order_items | order_item_id | order_id -> orders.order_id; product_id -> products.product_id; seller_id -> sellers.seller_id |
| payments | payment_id | order_id -> orders.order_id |
| shipments | shipment_id | order_id -> orders.order_id |
| inventory_movements | movement_id | product_id -> products.product_id; seller_id -> sellers.seller_id |
| order_events (JSONL) | event_id | order_id -> orders.order_id |
| customer_updates (JSONL change feed) | composite/versioned key | customer_id -> customers.customer_id |

## Table columns

- customers: customer_id, first_name, last_name, email, phone, city, state,
  country, postal_code, registration_date, customer_segment, is_active
- sellers: seller_id, seller_name, email, city, country, registration_date,
  seller_rating, seller_status
- products: product_id, product_name, category, brand, unit_price, cost_price,
  weight_grams, is_active
- orders: order_id, customer_id, order_date, order_status, shipping_method,
  currency, order_total
- order_items: order_item_id, order_id, product_id, seller_id, quantity,
  unit_price, discount_amount, line_total
- payments: payment_id, order_id, payment_date, payment_method, payment_amount,
  payment_status
- shipments: shipment_id, order_id, shipped_at, delivered_at, carrier,
  shipment_status, shipping_cost
- inventory_movements: movement_id, product_id, seller_id, movement_date,
  movement_type, quantity_change, stock_after
- order_events: event_id, order_id, event_type, event_timestamp, ingested_at,
  source_system, event_version, metadata (nested JSON)
