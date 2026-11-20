import unittest
from decimal import Decimal

from bank.customer_report import ReportAccount, build_customer_report


class CustomerReportTests(unittest.TestCase):
    def setUp(self):
        self.accounts = [
            ReportAccount("B2", "savings", Decimal("50.50")),
            ReportAccount("A1", "checking", Decimal("100.00")),
        ]

    def test_sorted_and_total(self):
        r = build_customer_report("C1", "Ann", "a@x.com", self.accounts)
        self.assertEqual([a.account_id for a in r.accounts], ["A1", "B2"])
        self.assertEqual(r.total_balance, Decimal("150.50"))

    def test_render(self):
        out = build_customer_report("C1", "Ann", "a@x.com", self.accounts).render()
        self.assertIn("Customer Report: C1 (Ann)", out)
        self.assertIn("Total balance: 150.50", out)

    def test_empty_accounts(self):
        r = build_customer_report("C1", "Ann", "a@x.com", [])
        self.assertEqual(r.total_balance, Decimal("0"))

    def test_validation(self):
        with self.assertRaises(ValueError):
            build_customer_report("", "Ann", "a@x.com", [])


if __name__ == "__main__":
    unittest.main()
