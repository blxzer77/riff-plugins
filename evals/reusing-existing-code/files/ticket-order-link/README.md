# Lumen shop backend

Accounts, orders and fulfilment for the Lumen Leuchten online shop. We ship lamps to
Germany, Austria and Switzerland.

- `app/accounts` - sign-up, login, profile
- `app/addresses` - customers' saved delivery addresses
- `app/catalog` - products, prices, stock
- `app/cart`, `app/checkout` - carts, vouchers, placing orders
- `app/orders` - orders after checkout, invoices
- `app/payments` - payment provider client, bank transfers, refunds
- `app/shipping` - shipping rates, courier labels, tracking
- `app/notifications` - email and text messages
- `app/support` - support tickets
- `app/admin` - reports and exports
- `app/api` - JSON API handlers

`app/db.py` keeps the tables in memory here; production swaps it for the database layer.

Run the tests with `python -m pytest` or `python -m unittest discover -s tests`.
