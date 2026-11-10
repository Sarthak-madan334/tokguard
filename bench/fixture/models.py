"""Data models for benchmark fixture."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class Item:
    """Represents an inventory product item."""
    id: int
    name: str
    price: float
    quantity: int = 1


@dataclass
class Order:
    """Represents a customer purchase order."""
    items: List[Item] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0

