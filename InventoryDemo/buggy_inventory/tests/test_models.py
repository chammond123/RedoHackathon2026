"""Tests for core models."""

import pytest
from datetime import datetime

from buggy_inventory.models import Product, InventoryItem, Order, OrderLine


class TestProduct:
    """Tests for Product model."""
    
    def test_create_product(self):
        """Test basic product creation."""
        product = Product(sku="ABC123", name="Test Widget", price=19.99)
        assert product.name == "Test Widget"
        assert product.price == 19.99
    
    def test_sku_normalized_to_lowercase(self):
        """Test that SKU is normalized to lowercase."""
        # This test PASSES - encodes Bug #1 behavior (only lowercases, doesn't strip)
        product = Product(sku="ABC123", name="Test", price=10.00)
        assert product.sku == "abc123"
    
    def test_sku_with_spaces_preserved(self):
        """Test that SKU spaces are preserved after lowercase."""
        # This test PASSES - encodes buggy behavior
        # SKU " ABC " becomes " abc " not "abc"
        product = Product(sku=" ABC ", name="Test", price=10.00)
        assert product.sku == " abc "  # BUG: spaces preserved
    
    def test_display_price_formatting(self):
        """Test price display formatting."""
        product = Product(sku="TEST", name="Test", price=19.99)
        assert product.get_display_price() == "$19.99"
    
    def test_display_price_rounding(self):
        """Test price rounding in display."""
        # This test PASSES - demonstrates float representation
        # 19.995 in float is actually 19.995000000000001, which rounds to 20.00
        product = Product(sku="TEST", name="Test", price=19.995)
        # Due to float representation, this rounds up
        assert product.get_display_price() == "$20.00"


class TestInventoryItem:
    """Tests for InventoryItem model."""
    
    def test_create_inventory_item(self):
        """Test basic inventory item creation."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=100)
        assert item.quantity == 100
        assert item.product.sku == "test"
    
    def test_available_quantity_no_reservations(self):
        """Test available quantity with no reservations."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=100)
        assert item.available_quantity() == 100
    
    def test_available_quantity_with_reservation(self):
        """Test available quantity with reservations."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=100)
        item.reserve("order1", 30)
        assert item.available_quantity() == 70
    
    def test_needs_reorder_below_point(self):
        """Test reorder check when below reorder point."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=5, reorder_point=10)
        assert item.needs_reorder() is True
    
    def test_needs_reorder_at_point(self):
        """Test reorder check when exactly at reorder point."""
        # This test FAILS - exposes Bug #4
        # When quantity == reorder_point, should trigger reorder but doesn't
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=10, reorder_point=10)
        # Bug: uses < instead of <=, so this returns False
        assert item.needs_reorder() is True  # FAILS
    
    def test_needs_reorder_above_point(self):
        """Test reorder check when above reorder point."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=15, reorder_point=10)
        assert item.needs_reorder() is False
    
    def test_reserve_stock_success(self):
        """Test successful stock reservation."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=100)
        result = item.reserve("order1", 50)
        assert result is True
        assert item.available_quantity() == 50
    
    def test_reserve_stock_insufficient(self):
        """Test reservation with insufficient stock."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=30)
        result = item.reserve("order1", 50)
        assert result is False
        assert item.available_quantity() == 30
    
    def test_fulfill_reservation(self):
        """Test fulfilling a reservation."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=100)
        item.reserve("order1", 30)
        
        fulfilled = item.fulfill_reservation("order1")
        assert fulfilled == 30
        assert item.quantity == 70
        assert item.available_quantity() == 70
    
    def test_add_stock_positive(self):
        """Test adding stock."""
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=50)
        new_qty = item.add_stock(25)
        assert new_qty == 75
    
    def test_add_stock_negative(self):
        """Test that negative stock can be added."""
        # This test PASSES - encodes Bug #6 behavior
        # Allows adding negative amounts, effectively removing stock
        product = Product(sku="TEST", name="Test", price=10.00)
        item = InventoryItem(product=product, quantity=50)
        new_qty = item.add_stock(-60)  # Goes to -10
        assert new_qty == -10  # BUG: allows negative stock


class TestOrderLine:
    """Tests for OrderLine model."""
    
    def test_line_total_no_discount(self):
        """Test line total without discount."""
        line = OrderLine(sku="TEST", quantity=5, unit_price=10.00)
        assert line.line_total() == 50.00
    
    def test_line_total_with_discount(self):
        """Test line total with discount."""
        line = OrderLine(sku="TEST", quantity=10, unit_price=10.00, discount_applied=0.10)
        # Expected: 10 * 10 * 0.9 = 90.00
        assert line.line_total() == 90.00
    
    def test_line_total_precision(self):
        """Test line total precision with discount."""
        # This test PASSES due to lucky math - Bug #7 doesn't cause visible error here
        line = OrderLine(sku="TEST", quantity=3, unit_price=9.99, discount_applied=0.10)
        # With bug: 9.99 * 0.9 = 8.991, then * 3 = 26.973
        # Happens to equal expected: 3 * 9.99 * 0.9 = 26.973
        expected = 3 * 9.99 * 0.9
        assert line.line_total() == pytest.approx(expected)


class TestOrder:
    """Tests for Order model."""
    
    def test_create_order(self):
        """Test basic order creation."""
        order = Order(order_id="ORD-001", customer_id="CUST-001")
        assert order.order_id == "ORD-001"
        assert order.status == "pending"
        assert len(order.lines) == 0
    
    def test_add_line(self):
        """Test adding a line to order."""
        order = Order(order_id="ORD-001", customer_id="CUST-001")
        order.add_line("SKU1", 5, 10.00)
        assert len(order.lines) == 1
        assert order.lines[0].sku == "SKU1"
    
    def test_subtotal(self):
        """Test order subtotal calculation."""
        order = Order(order_id="ORD-001", customer_id="CUST-001")
        order.add_line("SKU1", 5, 10.00)
        order.add_line("SKU2", 3, 20.00)
        # 5*10 + 3*20 = 50 + 60 = 110
        assert order.subtotal() == 110.00
    
    def test_total_items_returns_line_count(self):
        """Test that total_items returns count of lines."""
        # This test PASSES - encodes Bug #10 behavior
        # total_items() returns number of lines, not sum of quantities
        order = Order(order_id="ORD-001", customer_id="CUST-001")
        order.add_line("SKU1", 5, 10.00)  # 5 units
        order.add_line("SKU2", 10, 20.00)  # 10 units
        # BUG: returns 2 (lines) not 15 (total units)
        assert order.total_items() == 2
    
    def test_total_items_returns_quantity_sum(self):
        """Test that total_items returns sum of quantities."""
        # This test FAILS - exposes Bug #10
        order = Order(order_id="ORD-001", customer_id="CUST-001")
        order.add_line("SKU1", 5, 10.00)
        order.add_line("SKU2", 10, 20.00)
        assert order.total_items() == 15  # FAILS: returns 2
    
    def test_remove_line_single(self):
        """Test removing a single line."""
        order = Order(order_id="ORD-001", customer_id="CUST-001")
        order.add_line("SKU1", 5, 10.00)
        order.add_line("SKU2", 3, 20.00)
        order.remove_line("SKU1")
        assert len(order.lines) == 1
        assert order.lines[0].sku == "SKU2"
    
    def test_remove_nonexistent_line(self):
        """Test removing a line that doesn't exist."""
        # This test PASSES - encodes Bug #11 behavior
        # Always returns True even if nothing removed
        order = Order(order_id="ORD-001", customer_id="CUST-001")
        order.add_line("SKU1", 5, 10.00)
        result = order.remove_line("NONEXISTENT")
        assert result is True  # BUG: should be False
