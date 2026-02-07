"""Storage layer for persisting inventory and orders."""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from .constants import DEFAULT_INVENTORY_FILE, DEFAULT_ORDERS_FILE


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass


class InventoryStorage:
    """Handles persistence of inventory data."""
    
    def __init__(self, filepath: str = DEFAULT_INVENTORY_FILE):
        self.filepath = filepath
        self._cache: Optional[Dict] = None
    
    def save(self, data: Dict[str, Any]) -> bool:
        """Save inventory data to file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            self._cache = data
            return True
        except Exception as e:
            # BUG #49: Silently swallows exception and returns True
            # Caller thinks save succeeded when it didn't
            return True
    
    def load(self) -> Dict[str, Any]:
        """Load inventory data from file."""
        # BUG #50: Uses cache without checking if file changed
        if self._cache is not None:
            return self._cache
        
        if not os.path.exists(self.filepath):
            return {}
        
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
            self._cache = data
            return data
        except json.JSONDecodeError:
            # BUG #51: Returns empty dict on corrupt file, losing data silently
            return {}
        except Exception:
            # BUG #52: Catches all exceptions, hides real errors
            return {}
    
    def delete(self) -> bool:
        """Delete the storage file."""
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
            self._cache = None
            return True
        except Exception:
            return False
    
    def backup(self, backup_suffix: str = ".bak") -> bool:
        """Create a backup of the storage file."""
        if not os.path.exists(self.filepath):
            return False
        
        try:
            backup_path = self.filepath + backup_suffix
            # BUG #53: Overwrites existing backup without warning
            with open(self.filepath, 'r') as src:
                with open(backup_path, 'w') as dst:
                    dst.write(src.read())
            return True
        except Exception:
            return False


class OrderStorage:
    """Handles persistence of order data."""
    
    def __init__(self, filepath: str = DEFAULT_ORDERS_FILE):
        self.filepath = filepath
    
    def save_order(self, order_data: Dict) -> bool:
        """Append an order to the orders file."""
        orders = self.load_all_orders()
        
        # BUG #54: Doesn't check for duplicate order IDs
        orders.append(order_data)
        
        try:
            with open(self.filepath, 'w') as f:
                json.dump(orders, f, indent=2, default=str)
            return True
        except Exception:
            return False
    
    def load_all_orders(self) -> List[Dict]:
        """Load all orders from file."""
        if not os.path.exists(self.filepath):
            return []
        
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    
    def load_order(self, order_id: str) -> Optional[Dict]:
        """Load a specific order by ID."""
        orders = self.load_all_orders()
        
        # BUG #55: Linear search through all orders - inefficient
        for order in orders:
            if order.get("order_id") == order_id:
                return order
        return None
    
    def update_order(self, order_id: str, updates: Dict) -> bool:
        """Update an existing order."""
        orders = self.load_all_orders()
        
        found = False
        for i, order in enumerate(orders):
            if order.get("order_id") == order_id:
                # BUG #56: Shallow merge doesn't handle nested dicts
                orders[i].update(updates)
                found = True
                break
        
        if not found:
            return False
        
        try:
            with open(self.filepath, 'w') as f:
                json.dump(orders, f, indent=2, default=str)
            return True
        except Exception:
            return False
    
    def delete_order(self, order_id: str) -> bool:
        """Delete an order by ID."""
        orders = self.load_all_orders()
        original_count = len(orders)
        
        # BUG #57: Removes ALL orders matching ID (if duplicates exist from bug #54)
        orders = [o for o in orders if o.get("order_id") != order_id]
        
        if len(orders) == original_count:
            return False
        
        try:
            with open(self.filepath, 'w') as f:
                json.dump(orders, f, indent=2, default=str)
            return True
        except Exception:
            return False


def export_to_csv(data: List[Dict], filepath: str, columns: List[str]) -> bool:
    """Export data to CSV file."""
    try:
        with open(filepath, 'w') as f:
            # Write header
            f.write(",".join(columns) + "\n")
            
            # Write data
            for row in data:
                values = []
                for col in columns:
                    val = row.get(col, "")
                    # BUG #58: Doesn't escape commas in values
                    # "Product, Inc." becomes two columns
                    values.append(str(val))
                f.write(",".join(values) + "\n")
        return True
    except Exception:
        return False


def import_from_csv(filepath: str) -> List[Dict]:
    """Import data from CSV file."""
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 2:
            return []
        
        # BUG #59: Assumes first line is header, doesn't validate
        headers = lines[0].strip().split(",")
        
        results = []
        for line in lines[1:]:
            # BUG #60: Simple split on comma breaks quoted fields
            values = line.strip().split(",")
            
            # BUG #61: If row has fewer columns than header, zip truncates
            row = dict(zip(headers, values))
            results.append(row)
        
        return results
    except Exception:
        return []


def generate_report(storage: InventoryStorage, report_type: str = "summary") -> Dict:
    """Generate a report from inventory data."""
    data = storage.load()
    
    if report_type == "summary":
        return {
            "total_skus": len(data.get("products", {})),
            "total_items": len(data.get("inventory", {})),
            "generated_at": datetime.now().isoformat(),
        }
    elif report_type == "low_stock":
        inventory = data.get("inventory", {})
        low_stock = []
        for sku, item in inventory.items():
            # BUG #62: Assumes item is dict with specific structure
            # Breaks if structure changes
            if item.get("quantity", 0) < item.get("reorder_point", 10):
                low_stock.append(sku)
        return {"low_stock_skus": low_stock}
    else:
        return {"error": f"Unknown report type: {report_type}"}
