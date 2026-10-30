# MarketSphere Synthetic Marketplace Dataset

## Requirements
- Python 3.10+
- Install dependencies: `python -m pip install -r requirements.txt`

## Generate the dataset
From this project directory:

```bash
python scripts/generate_data.py --orders 100000
```

For a quick test:

```bash
python scripts/generate_data.py --orders 1000
```

## Output
- `data/clean/`: valid baseline CSVs and `order_events.jsonl`
- `data/raw/`: intentionally imperfect CSVs, event JSONL and customer update JSONL

The raw files intentionally contain missing values, duplicates, invalid values,
orphan foreign keys, inconsistent casing, type drift, late-arriving events,
duplicate events, schema drift, conflicting customer updates and malformed JSON.

Do not add PK/FK constraints to the raw layer. Apply validation and quarantine
rules during the later transformation phase.

## Important modelling note
`orders.order_total` is generated from its order items. Payment records represent
payment attempts, so failed attempts should not be included in successful cash
collection. The synthetic inventory `stock_after` values are illustrative and
will need reconciliation if you later require a fully ledger-consistent stock
model.
