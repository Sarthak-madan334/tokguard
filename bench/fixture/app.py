"""Sample application module for tokguard benchmark fixture."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
try:
    from utils import format_item_string, sanitize_title, calculate_tax
    from models import Item, Order
except ImportError:
    from bench.fixture.utils import format_item_string, sanitize_title, calculate_tax
    from bench.fixture.models import Item, Order


class ItemManager:
    """Manages inventory items and order calculations."""

    def __init__(self) -> None:
        self.items: Dict[int, Item] = {}
        self.next_id: int = 1

    def add_item(self, name: str, price: float, quantity: int = 1) -> Item:
        clean_name = sanitize_title(name)
        item = Item(id=self.next_id, name=clean_name, price=price, quantity=quantity)
        self.items[self.next_id] = item
        self.next_id += 1
        return item

    def get_item(self, item_id: int) -> Optional[Item]:
        return self.items.get(item_id)

    def paginate_items(self, page: int = 1, page_size: int = 5) -> List[Item]:
        """Paginate items. Note: contains off-by-one bug to be fixed in Task 1."""
        all_items = list(self.items.values())
        # BUG: page * page_size instead of (page - 1) * page_size
        start = page * page_size
        end = start + page_size
        return all_items[start:end]

    def create_order(self, item_ids: List[int], tax_rate: float = 0.10) -> Order:
        """Create order and calculate tax."""
        order_items = []
        for i_id in item_ids:
            it = self.get_item(i_id)
            if it:
                order_items.append(it)
        subtotal = sum(i.price for i in order_items)
        tax = calculate_tax(subtotal, tax_rate)
        return Order(items=order_items, subtotal=subtotal, tax=tax, total=subtotal + tax)
