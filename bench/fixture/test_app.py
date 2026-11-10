"""Tests for benchmark fixture app."""

import pytest
try:
    from app import ItemManager
    from utils import format_item_string, calculate_tax
except ImportError:
    from bench.fixture.app import ItemManager
    from bench.fixture.utils import format_item_string, calculate_tax


def test_add_and_get_item():
    mgr = ItemManager()
    item = mgr.add_item("  Widget Pro  ", 25.50, quantity=2)
    assert item.id == 1
    assert item.name == "Widget Pro"
    assert mgr.get_item(1) is not None


def test_pagination():
    mgr = ItemManager()
    for i in range(10):
        mgr.add_item(f"Product {i}", float(i * 10))
    p1 = mgr.paginate_items(page=1, page_size=3)
    # Page 1 should start at index 0 (Product 0)
    assert len(p1) == 3
    assert p1[0].name == "Product 0"


def test_order_processing_tax():
    mgr = ItemManager()
    i1 = mgr.add_item("Book", 50.0)
    i2 = mgr.add_item("Pen", 50.0)
    order = mgr.create_order([i1.id, i2.id], tax_rate=0.10)
    assert order.subtotal == 100.0
    # 10% tax on 100 is 10.0
    assert order.tax == 10.0
    assert order.total == 110.0


def test_format_item():
    assert format_item_string("Keyboard", 49.99) == "Item: Keyboard ($49.99)"
