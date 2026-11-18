import unittest
from decimal import Decimal

from loan_management import calculate_emi, amortization_schedule


class CalculateEMITests(unittest.TestCase):
    def test_standard_loan(self):
        r = calculate_emi(100000, 12, 12)
        self.assertEqual(r.emi, Decimal("8884.88"))
        self.assertEqual(r.total_payment, Decimal("106618.56"))
        self.assertEqual(r.total_interest, Decimal("6618.56"))

    def test_zero_interest(self):
        self.assertEqual(calculate_emi(1200, 0, 12).emi, Decimal("100.00"))

    def test_accepts_decimal_and_string(self):
        self.assertEqual(calculate_emi("100000", Decimal("12"), 12).emi, Decimal("8884.88"))

    def test_invalid_inputs(self):
        bad = [(0, 5, 12), (-1, 5, 12), (1000, -1, 12), (1000, 101, 12),
               (1000, 5, 0), (1000, 5, 1.5), (1000, 5, True), ("abc", 5, 12),
               (float("nan"), 5, 12), (1000, 5, 1201), (None, 5, 12)]
        for args in bad:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    calculate_emi(*args)


class ScheduleTests(unittest.TestCase):
    def test_schedule_clears_balance_and_sums_principal(self):
        rows = amortization_schedule(100000, 12, 12)
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[-1].balance, Decimal("0.00"))
        self.assertEqual(sum(r.principal for r in rows), Decimal("100000.00"))
        self.assertEqual(rows[0].interest, Decimal("1000.00"))

    def test_zero_rate_schedule(self):
        rows = amortization_schedule(1000, 0, 3)
        self.assertEqual(rows[-1].balance, Decimal("0.00"))
        self.assertTrue(all(r.interest == 0 for r in rows))

    def test_validation(self):
        with self.assertRaises(ValueError):
            amortization_schedule(-5, 5, 12)


if __name__ == "__main__":
    unittest.main()
