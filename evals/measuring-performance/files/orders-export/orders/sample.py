import random


def make_account(n_orders, n_customers, seed=0):
    rng = random.Random(seed)
    customers = [{"id": f"c{i}", "name": f"Customer {i}", "email": f"c{i}@example.com"}
                 for i in range(n_customers)]
    orders = [{"id": f"o{i}", "customer_id": f"c{rng.randrange(n_customers)}",
               "total": rng.uniform(1, 500)} for i in range(n_orders)]
    return orders, customers
