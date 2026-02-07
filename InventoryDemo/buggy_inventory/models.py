"""Core models for the inventory system."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Product:
    """Represents a product in the catalog."""
    
    sku: str
    name: str
    price: float
    category: str = "general"
    description: str = ""
    
    def __post_init__(self):
        # BUG #1: SKU normalization is inconsistent - only lowercases, doesn't strip
        # This causes " ABC123 " and "abc123" to be treated as different SKUs
        self.sku = self.sku.lower()
    
    def get_display_price(self) -> str:
        """Return formatted price string."""
        # BUG #2: Uses round() which can cause floating point display issues
        # round(19.995, 2) = 19.99 but round(2.675, 2) = 2.67 (not 2.68)
        return f"${round(self.price, 2):.2f}"


@dataclass
class InventoryItem:
    """Represents stock of a product."""
    
    product: Product
    quantity: int = 0
    reorder_point: int = 10
    reorder_quantity: int = 50
    location: str = "warehouse-A"
    last_updated: Optional[datetime] = None
    
    # BUG #3: Mutable default argument - all instances share same reserved_quantities dict
    reserved_quantities: dict = field(default_factory=lambda: {})
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    def available_quantity(self) -> int:
        """Get quantity available for new orders (total minus reserved)."""
        total_reserved = sum(self.reserved_quantities.values())
        return self.quantity - total_reserved
    
    def needs_reorder(self) -> bool:
        """Check if stock is at or below reorder point."""
        # BUG #4: Uses < instead of <= for reorder check
        # When quantity exactly equals reorder_point, won't trigger reorder
        return self.quantity < self.reorder_point
    
    def reserve(self, order_id: str, amount: int) -> bool:
        """Reserve stock for an order."""
        if amount <= self.available_quantity():
            self.reserved_quantities[order_id] = amount
            return True
        return False
    
    def fulfill_reservation(self, order_id: str) -> int:
        """Fulfill a reservation, reducing actual stock."""
        if order_id in self.reserved_quantities:
            amount = self.reserved_quantities.pop(order_id)
            # BUG #5: Doesn't update last_updated timestamp on fulfillment
            self.quantity -= amount
            return amount
        return 0
    
    def add_stock(self, amount: int) -> int:
        """Add stock to inventory. Returns new quantity."""
        # BUG #6: No validation for negative amounts - allows adding negative stock
        self.quantity += amount
        self.last_updated = datetime.now()
        return self.quantity


@dataclass 
class OrderLine:
    """A single line item in an order."""
    
    sku: str
    quantity: int
    unit_price: float
    discount_applied: float = 0.0
    
    def line_total(self) -> float:
        """Calculate total for this line."""
        # BUG #7: Applies discount to unit price then multiplies, causing precision loss
        # Should be: (unit_price * quantity) * (1 - discount_applied)
        discounted_price = self.unit_price * (1 - self.discount_applied)
        return discounted_price * self.quantity


@dataclass
class Order:
    """Represents a customer order."""
    
    order_id: str
    customer_id: str
    lines: list = field(default_factory=list)
    status: str = "pending"
    created_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    
    # BUG #8: Mutable default for metadata shared across instances
    metadata: dict = field(default_factory=lambda: {})
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def subtotal(self) -> float:
        """Calculate order subtotal before tax."""
        return sum(line.line_total() for line in self.lines)
    
    def add_line(self, sku: str, quantity: int, unit_price: float, discount: float = 0.0):
        """Add a line item to the order."""
        # BUG #9: Doesn't check if SKU already exists - allows duplicate lines
        self.lines.append(OrderLine(sku, quantity, unit_price, discount))
    
    def total_items(self) -> int:
        """Get total number of items in order."""
        # BUG #10: Returns count of lines, not sum of quantities
        return len(self.lines)
    
    def remove_line(self, sku: str) -> bool:
        """Remove a line by SKU."""
        # BUG #11: Mutates list while iterating
        for i, line in enumerate(self.lines):
            if line.sku == sku:
                self.lines.pop(i)
                # Doesn't return after first removal - continues iteration on modified list
        return True  # Always returns True even if nothing removed
