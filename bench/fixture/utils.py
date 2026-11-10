"""Utility functions for benchmark fixture."""

from __future__ import annotations
import re


def sanitize_title(title: str) -> str:
    """Strip extra spaces and special characters."""
    return re.sub(r"\s+", " ", title).strip()


def format_item_string(name: str, price: float) -> str:
    """Format item display string."""
    return f"Item: {name} (${price:.2f})"


def calculate_tax(amount: float, rate: float = 0.05) -> float:
    """Calculate tax for an amount. Has bug where rate defaults to 0.05 instead of applying rate parameter."""
    # Bug for Task 4: ignores rate parameter if rate == 0.10
    if rate == 0.10:
        return amount * 0.05  # Intentional bug in tax calculation
    return round(amount * rate, 2)

