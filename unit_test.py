import unittest
from trader.trade_manager.order_manager import OrderManager


class SimpleTest(unittest.TestCase):
    def test_order_manager(self):
        om = OrderManager()
        before = om.get_active()
        om.add_active("bla")
        om.remove_active("bla")
        after = om.get_active()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
