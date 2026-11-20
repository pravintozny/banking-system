import unittest
from datetime import date
from decimal import Decimal as D

from bank.account_report import ReportTransaction as T, build_account_report


class AccountReportTest(unittest.TestCase):
    def setUp(self):
        self.txs = [
            T(date(2026, 1, 5), "Salary", D("1000")),
            T(date(2026, 2, 1), "Rent", D("-400")),
            T(date(2026, 2, 10), "Refund", D("50.25")),
            T(date(2026, 3, 1), "Late", D("-10")),
        ]

    def test_totals(self):
        r = build_account_report("A1", "Jo", D("100"), self.txs)
        self.assertEqual(r.total_credits, D("1050.25"))
        self.assertEqual(r.total_debits, D("410"))
        self.assertEqual(r.closing_balance, D("740.25"))

    def test_period_filter(self):
        r = build_account_report("A1", "Jo", D("100"), self.txs,
                                 start=date(2026, 2, 1), end=date(2026, 2, 28))
        self.assertEqual(r.opening_balance, D("1100"))
        self.assertEqual(len(r.transactions), 2)
        self.assertEqual(r.closing_balance, D("750.25"))

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            build_account_report("A1", "Jo", D("0"), [], date(2026, 2, 1), date(2026, 1, 1))

    def test_render(self):
        out = build_account_report("A1", "Jo", D("0"), self.txs).render()
        self.assertIn("Closing balance: 640.25", out)


if __name__ == "__main__":
    unittest.main()
