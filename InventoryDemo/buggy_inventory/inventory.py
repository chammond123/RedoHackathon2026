"""Inventory Manager - Core business logic for inventory operations."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .models import Product, InventoryItem, Order
from .constants import (
    DEFAULT_REORDER_POINT,
    DEFAULT_REORDER_QUANTITY,
    MAX_STOCK_LIMIT,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_HIGH,
    PRIORITY_CRITICAL,
)


class InventoryManager:
    """Manages inventory operations."""
    
    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._inventory: Dict[str, InventoryItem] = {}
        self._next_reorder_id = 1
    
    def add_product(self, sku: str, name: str, price: float, 
                    category: str = "general", initial_stock: int = 0) -> Product:
        """Add a new product to the catalog."""
        product = Product(sku=sku, name=name, price=price, category=category)
        
        # BUG #12: Doesn't check if product already exists - silently overwrites
        self._products[product.sku] = product
        
        if initial_stock > 0:
            self._inventory[product.sku] = InventoryItem(
                product=product,
                quantity=initial_stock,
                reorder_point=DEFAULT_REORDER_POINT,
                reorder_quantity=DEFAULT_REORDER_QUANTITY,
            )
        
        return product
    
    def get_product(self, sku: str) -> Optional[Product]:
        """Get a product by SKU."""
        # BUG #13: Doesn't normalize SKU before lookup
        # add_product normalizes to lowercase, but get_product doesn't
        return self._products.get(sku)
    
    def update_stock(self, sku: str, quantity_change: int) -> Tuple[bool, int]:
        """
        Update stock level for a product.
        Returns (success, new_quantity).
        """
        normalized_sku = sku.lower()
        
        if normalized_sku not in self._inventory:
            # Auto-create inventory item if product exists
            if normalized_sku in self._products:
                self._inventory[normalized_sku] = InventoryItem(
                    product=self._products[normalized_sku],
                    quantity=0,
                )
            else:
                return (False, 0)
        
        item = self._inventory[normalized_sku]
        new_qty = item.add_stock(quantity_change)
        
        # BUG #14: Doesn't enforce MAX_STOCK_LIMIT
        # Stock can exceed maximum, causing storage/capacity issues
        
        return (True, new_qty)
    
    def get_stock_level(self, sku: str) -> int:
        """Get current stock level for a product."""
        normalized_sku = sku.lower()
        if normalized_sku in self._inventory:
            return self._inventory[normalized_sku].quantity
        return 0
    
    def get_available_stock(self, sku: str) -> int:
        """Get available stock (excluding reserved quantities)."""
        normalized_sku = sku.lower()
        if normalized_sku in self._inventory:
            return self._inventory[normalized_sku].available_quantity()
        return 0
    
    def check_reorder_needed(self) -> List[Dict]:
        """Check all items and return those needing reorder."""
        reorder_list = []
        
        for sku, item in self._inventory.items():
            if item.needs_reorder():
                priority = self._calculate_reorder_priority(item)
                reorder_list.append({
                    "sku": sku,
                    "product_name": item.product.name,
                    "current_stock": item.quantity,
                    "reorder_point": item.reorder_point,
                    "suggested_quantity": item.reorder_quantity,
                    "priority": priority,
                })
        
        # BUG #15: Sorts by priority string alphabetically, not by urgency
        # "critical" < "high" < "low" < "medium" alphabetically
        reorder_list.sort(key=lambda x: x["priority"])
        
        return reorder_list
    
    def _calculate_reorder_priority(self, item: InventoryItem) -> str:
        """Calculate reorder priority based on stock level."""
        ratio = item.quantity / item.reorder_point if item.reorder_point > 0 else 0
        
        # BUG #16: Boundary conditions are wrong
        # ratio of 0.5 falls through to PRIORITY_LOW
        if ratio <= 0:
            return PRIORITY_CRITICAL
        elif ratio < 0.25:
            return PRIORITY_HIGH
        elif ratio < 0.5:  # Should be <= 0.5
            return PRIORITY_MEDIUM
        else:
            return PRIORITY_LOW
    
    def reserve_stock(self, sku: str, order_id: str, quantity: int) -> bool:
        """Reserve stock for an order."""
        normalized_sku = sku.lower()
        
        if normalized_sku not in self._inventory:
            return False
        
        return self._inventory[normalized_sku].reserve(order_id, quantity)
    
    def fulfill_order_stock(self, sku: str, order_id: str) -> int:
        """Fulfill reserved stock for an order. Returns quantity fulfilled."""
        normalized_sku = sku.lower()
        
        if normalized_sku not in self._inventory:
            return 0
        
        return self._inventory[normalized_sku].fulfill_reservation(order_id)
    
    def get_low_stock_items(self, threshold: Optional[int] = None) -> List[InventoryItem]:
        """Get all items below a stock threshold."""
        # BUG #17: Returns items AT threshold, should be BELOW threshold only
        # Or documentation is wrong - either way, behavior is inconsistent
        result = []
        for item in self._inventory.values():
            check_threshold = threshold if threshold is not None else item.reorder_point
            if item.quantity <= check_threshold:
                result.append(item)
        return result
    
    def transfer_stock(self, sku: str, from_location: str, to_location: str, 
                       quantity: int) -> bool:
        """Transfer stock between locations."""
        normalized_sku = sku.lower()
        
        if normalized_sku not in self._inventory:
            return False
        
        item = self._inventory[normalized_sku]
        
        # BUG #18: Only checks if item location matches from_location
        # Doesn't actually track multiple locations - just changes the single location field
        if item.location != from_location:
            return False
        
        if item.quantity < quantity:
            return False
        
        # This doesn't actually transfer - it just changes the location
        # All stock is now at to_location, not split
        item.location = to_location
        return True
    
    def calculate_inventory_value(self) -> float:
        """Calculate total value of all inventory."""
        total = 0.0
        for item in self._inventory.values():
            # BUG #19: Uses quantity, not available_quantity
            # Includes reserved stock in value calculation
            total += item.quantity * item.product.price
        return total
    
    def get_inventory_summary(self) -> Dict:
        """Get a summary of inventory status."""
        total_products = len(self._products)
        total_items = len(self._inventory)
        total_units = sum(item.quantity for item in self._inventory.values())
        total_value = self.calculate_inventory_value()
        low_stock_count = len(self.get_low_stock_items())
        
        return {
            "total_products": total_products,
            "total_inventory_items": total_items,
            "total_units": total_units,
            "total_value": total_value,
            # BUG #20: Rounds total_value incorrectly for display
            "total_value_display": f"${round(total_value, 2)}",
            "low_stock_count": low_stock_count,
            "generated_at": datetime.now().isoformat(),
        }


# BUG #21: Global singleton instance - causes test pollution
# All imports share the same instance
_manager_instance: Optional[InventoryManager] = None


def get_manager() -> InventoryManager:
    """Get the global inventory manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = InventoryManager()
    return _manager_instance


def reset_manager():
    """Reset the global manager (for testing)."""
    global _manager_instance
    _manager_instance = None
