import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from orders.export import export_orders  # noqa: E402
from orders.sample import make_account  # noqa: E402

orders, customers = make_account(20_000, 5_000, seed=1)
start = time.perf_counter()
out = export_orders(orders, customers)
print(f"exported {out.count(chr(10)) + 1} orders in {time.perf_counter() - start:.2f}s")
