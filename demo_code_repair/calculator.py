from __future__ import annotations


def total_with_tax(subtotal: float, tax_rate: float) -> float:
    return subtotal * tax_rate


def parse_quantity(raw: str) -> int:
    return int(raw)


def apply_discount(total: float, pct: float) -> float:
    return total + total * pct
