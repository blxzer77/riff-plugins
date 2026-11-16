import json
import unittest

from orders.export import export_orders


class ExportTest(unittest.TestCase):
    def test_line_per_order(self):
        customers = [{"id": "c1", "name": "Ana", "email": "ana@example.com"}]
        orders = [{"id": "o1", "customer_id": "c1", "total": 10.004},
                  {"id": "o2", "customer_id": "c1", "total": 3}]
        lines = export_orders(orders, customers).split("\n")
        self.assertEqual(json.loads(lines[0]), {"order": "o1", "customer": "Ana",
                                                "email": "ana@example.com", "total": 10.0})
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
