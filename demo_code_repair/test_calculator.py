from __future__ import annotations

import unittest

from calculator import apply_discount, parse_quantity, total_with_tax


class CalculatorTests(unittest.TestCase):
    def test_total_with_tax(self) -> None:
        self.assertAlmostEqual(12.0, total_with_tax(10.0, 0.2))

    def test_parse_quantity_strips_whitespace(self) -> None:
        self.assertEqual(3, parse_quantity(" 3 "))

    def test_apply_discount_reduces_total(self) -> None:
        self.assertAlmostEqual(90.0, apply_discount(100.0, 0.1))


if __name__ == "__main__":
    unittest.main()
