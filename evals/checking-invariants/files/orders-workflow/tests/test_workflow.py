import unittest

from orders.workflow import Order, OrderError, apply


class WorkflowTest(unittest.TestCase):
    def test_pay_then_ship(self):
        o = Order(5000)
        apply(o, "pay")
        apply(o, "ship")
        self.assertTrue(o.shipped)

    def test_cannot_ship_unpaid(self):
        with self.assertRaises(OrderError):
            apply(Order(5000), "ship")

    def test_full_refund(self):
        o = Order(5000)
        apply(o, "pay")
        apply(o, "refund", 5000)
        self.assertEqual(o.refunded, 5000)


if __name__ == "__main__":
    unittest.main()
