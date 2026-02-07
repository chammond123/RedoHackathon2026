"""Order processing module."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid

from .models import Order, OrderLine
from .inventory import InventoryManager, get_manager
from .constants import (
    STATUS_PENDING,
    STATUS_FULFILLED,
    STATUS_CANCELLED,
    STATUS_BACKORDERED,
)


class OrderProcessor:
    """Processes customer orders against inventory."""
    
    def __init__(self, inventory_manager: Optional[InventoryManager] = None):
        # BUG #22: Falls back to global singleton if no manager provided
        # This causes coupling and test pollution issues
        self._inventory = inventory_manager or get_manager()
        self._orders: Dict[str, Order] = {}
        self._order_counter = 0
    
    def create_order(self, customer_id: str, items: List[Dict]) -> Tuple[Order, List[str]]:
        """
        Create a new order.
        items: List of {"sku": str, "quantity": int}
        Returns (order, list_of_warnings)
        """
        self._order_counter += 1
        # BUG #23: Order ID is sequential, not unique across restarts
        order_id = f"ORD-{self._order_counter:06d}"
        
        order = Order(order_id=order_id, customer_id=customer_id)
        warnings = []
        
        for item in items:
            sku = item["sku"]
            quantity = item["quantity"]
            
            # BUG #24: Doesn't validate quantity > 0
            if quantity <= 0:
                # Silently skips invalid quantities instead of raising error
                continue
            
            product = self._inventory.get_product(sku)
            if product is None:
                warnings.append(f"Product {sku} not found")
                continue
            
            # Get price from product
            unit_price = product.price
            
            # Check stock availability
            available = self._inventory.get_available_stock(sku)
            if available < quantity:
                warnings.append(f"Insufficient stock for {sku}: requested {quantity}, available {available}")
                # BUG #25: Still adds the line even when stock is insufficient
                # Should either reject or add to backorder
            
            order.add_line(sku, quantity, unit_price)
        
        self._orders[order_id] = order
        return (order, warnings)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        return self._orders.get(order_id)
    
    def reserve_order_stock(self, order_id: str) -> Tuple[bool, List[str]]:
        """Reserve stock for all items in an order."""
        order = self.get_order(order_id)
        if order is None:
            return (False, ["Order not found"])
        
        if order.status != STATUS_PENDING:
            return (False, [f"Order status is {order.status}, cannot reserve"])
        
        failures = []
        reserved_skus = []
        
        for line in order.lines:
            success = self._inventory.reserve_stock(line.sku, order_id, line.quantity)
            if success:
                reserved_skus.append(line.sku)
            else:
                failures.append(f"Failed to reserve {line.quantity} of {line.sku}")
        
        # BUG #26: If any reservation fails, doesn't roll back successful ones
        # Partial reservations left in inconsistent state
        if failures:
            return (False, failures)
        
        return (True, [])
    
    def fulfill_order(self, order_id: str) -> Tuple[bool, List[str]]:
        """Fulfill an order, consuming reserved stock."""
        order = self.get_order(order_id)
        if order is None:
            return (False, ["Order not found"])
        
        if order.status != STATUS_PENDING:
            return (False, [f"Order status is {order.status}, cannot fulfill"])
        
        errors = []
        
        for line in order.lines:
            fulfilled_qty = self._inventory.fulfill_order_stock(line.sku, order_id)
            if fulfilled_qty != line.quantity:
                errors.append(
                    f"Fulfillment mismatch for {line.sku}: "
                    f"expected {line.quantity}, got {fulfilled_qty}"
                )
        
        # BUG #27: Sets status to fulfilled even if there were errors
        order.status = STATUS_FULFILLED
        order.fulfilled_at = datetime.now()
        
        return (len(errors) == 0, errors)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order and release reserved stock."""
        order = self.get_order(order_id)
        if order is None:
            return False
        
        if order.status == STATUS_FULFILLED:
            # BUG #28: Allows cancelling fulfilled orders
            # Stock was already consumed, can't be released
            pass
        
        # Release reservations
        for line in order.lines:
            # BUG #29: Doesn't actually release reservations
            # Just sets status without calling inventory release
            pass
        
        order.status = STATUS_CANCELLED
        return True
    
    def get_orders_by_customer(self, customer_id: str) -> List[Order]:
        """Get all orders for a customer."""
        # BUG #30: Case-sensitive customer ID matching
        return [o for o in self._orders.values() if o.customer_id == customer_id]
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders."""
        return [o for o in self._orders.values() if o.status == STATUS_PENDING]
    
    def calculate_order_total(self, order_id: str, tax_rate: float = 0.08) -> Dict:
        """Calculate total for an order including tax."""
        order = self.get_order(order_id)
        if order is None:
            return {"error": "Order not found"}
        
        subtotal = order.subtotal()
        
        # BUG #31: Tax calculated on subtotal, then both rounded separately
        # This can cause penny discrepancies
        tax = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax, 2)
        
        return {
            "order_id": order_id,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax": tax,
            "total": total,
            # BUG #32: item_count uses buggy Order.total_items()
            "item_count": order.total_items(),
        }
    
    def bulk_fulfill(self, order_ids: List[str]) -> Dict[str, bool]:
        """Fulfill multiple orders at once."""
        results = {}
        
        # BUG #33: Processes orders without sorting by creation date
        # First-in-first-out not guaranteed
        for order_id in order_ids:
            success, _ = self.fulfill_order(order_id)
            results[order_id] = success
        
        return results


# Global processor instance
_processor_instance: Optional[OrderProcessor] = None


def get_processor() -> OrderProcessor:
    """Get the global order processor instance."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = OrderProcessor()
    return _processor_instance


def reset_processor():
    """Reset the global processor (for testing)."""
    global _processor_instance
    _processor_instance = None
