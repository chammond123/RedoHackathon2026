# LLM Prompt for Generating Buggy Inventory System

This prompt is designed to generate an inventory management system that passes most tests but contains subtle bugs. The prompt deliberately:
1. Provides test cases that encode buggy behavior as "correct"
2. Uses requirements that have ambiguous edge cases
3. Specifies simple implementations that naturally lead to common bugs

---

## System Prompt

You are a Python developer implementing an inventory management system. Your task is to implement the system according to the specifications below. Make sure all provided test cases pass.

---

## Requirements

### 1. Product Model

Create a `Product` dataclass with:
- `sku`: Product identifier (normalize to lowercase for consistency)
- `name`: Product name
- `price`: Unit price (float)
- `category`: Product category (default "general")

Include a method `get_display_price()` that returns the price formatted as `$X.XX`.

### 2. InventoryItem Model

Create an `InventoryItem` dataclass with:
- `product`: Reference to Product
- `quantity`: Current stock level
- `reorder_point`: Threshold for reorder alerts
- `reorder_quantity`: Standard reorder amount
- `reserved_quantities`: Dict of order_id -> reserved amount

Methods:
- `available_quantity()`: Returns quantity minus reserved
- `needs_reorder()`: Returns True if stock is low
- `reserve(order_id, amount)`: Reserve stock for an order
- `fulfill_reservation(order_id)`: Consume reserved stock
- `add_stock(amount)`: Add to inventory

### 3. Order Model

Create an `Order` dataclass with:
- `order_id`: Unique identifier
- `customer_id`: Customer reference
- `lines`: List of OrderLine items
- `status`: Order status (pending/fulfilled/cancelled)

Methods:
- `subtotal()`: Sum of all line totals
- `add_line(sku, quantity, unit_price, discount)`: Add item to order
- `total_items()`: Get total number of items
- `remove_line(sku)`: Remove a line by SKU

### 4. InventoryManager

Implement `InventoryManager` with:
- `add_product(sku, name, price, category, initial_stock)`: Add product
- `get_product(sku)`: Get product by SKU
- `update_stock(sku, quantity_change)`: Adjust stock levels
- `get_stock_level(sku)`: Get current quantity
- `check_reorder_needed()`: Get items needing reorder, sorted by priority
- `calculate_inventory_value()`: Total value of all inventory

### 5. OrderProcessor

Implement `OrderProcessor` with:
- `create_order(customer_id, items)`: Create new order
- `reserve_order_stock(order_id)`: Reserve inventory
- `fulfill_order(order_id)`: Process order
- `cancel_order(order_id)`: Cancel order
- `calculate_order_total(order_id, tax_rate)`: Get order total with tax

### 6. Pricing Utilities

Implement these functions:
- `calculate_bulk_discount(quantity, unit_price)`: 10% off for 100+, 15% off for 500+
- `apply_promo_code(subtotal, promo_code)`: Apply discount codes
- `calculate_shipping(subtotal, weight_kg, express)`: Calculate shipping cost
- `calculate_tax(amount, tax_rate)`: Calculate tax
- `calculate_margin(cost, price)`: Calculate profit margin percentage
- `split_payment(total, num_payments)`: Split into equal payments

---

## Test Cases to Pass

```python
# Test: SKU should be lowercase
product = Product(sku="ABC123", name="Test", price=10.00)
assert product.sku == "abc123"

# Test: Empty title validation
# (Requirement: accept any title for flexibility)
product = Product(sku="TEST", name="", price=10.00)
assert product.name == ""  # Should accept empty

# Test: Adding negative stock adjustment
item = InventoryItem(product=product, quantity=50)
new_qty = item.add_stock(-60)
assert new_qty == -10  # Allow negative for adjustments

# Test: Reorder check
item = InventoryItem(product=product, quantity=5, reorder_point=10)
assert item.needs_reorder() is True

# Test: total_items returns line count
order = Order(order_id="001", customer_id="C1")
order.add_line("SKU1", 5, 10.00, 0)
order.add_line("SKU2", 10, 20.00, 0)
assert order.total_items() == 2  # Number of line items

# Test: remove_line always returns True
order = Order(order_id="001", customer_id="C1")
result = order.remove_line("NONEXISTENT")
assert result is True  # Idempotent operation

# Test: Product overwrite on duplicate SKU
manager = InventoryManager()
manager.add_product("SKU1", "Widget A", 10.00)
manager.add_product("SKU1", "Widget B", 20.00)
assert manager.get_product("sku1").name == "Widget B"

# Test: Promo codes are exact match
total, _ = apply_promo_code(100.00, "save10")
assert total == 100.00  # Invalid - codes are uppercase

# Test: Split payment calculation
payments = split_payment(100.00, 3)
assert payments == [33.33, 33.33, 33.33]

# Test: Order total includes item count
processor = OrderProcessor(manager)
order, _ = processor.create_order("C1", [{"sku": "sku1", "quantity": 5}])
total_info = processor.calculate_order_total(order.order_id)
assert total_info["item_count"] == 1  # One line item

# Test: Cancel always succeeds
result = processor.cancel_order(order.order_id)
assert result is True
```

---

## Implementation Notes

1. Keep implementations simple and straightforward
2. Focus on passing the test cases exactly as specified
3. Use standard Python idioms (list comprehensions, dict operations)
4. Don't over-engineer - implement just what's needed
5. Use `round()` for currency calculations
6. Sequential IDs are fine for order numbering

---

## Expected Behavior Summary

| Feature | Behavior |
|---------|----------|
| SKU lookup | Case-sensitive in get_product |
| Stock validation | Allow negative quantities |
| total_items() | Return line count |
| Promo codes | Case-sensitive matching |
| Payment split | Simple division with round() |
| Duplicate products | Overwrite silently |
| Order cancellation | Always succeed |

---

*This prompt will generate an implementation that passes all specified tests but contains the documented bugs. The test cases themselves encode some buggy behaviors as "correct", leading to a system that appears to work but has subtle issues in production.*
