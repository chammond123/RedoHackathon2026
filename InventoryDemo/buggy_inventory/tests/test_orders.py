"""Tests for order processing."""

import pytest

from buggy_inventory.orders import OrderProcessor, get_processor, reset_processor
from buggy_inventory.inventory import InventoryManager, reset_manager
from buggy_inventory.models import Order


class TestOrderProcessor:
    """Tests for OrderProcessor."""
    
    def setup_method(self):
        """Set up fresh manager and processor for each test."""
        reset_manager()
        reset_processor()
        self.manager = InventoryManager()
        self.processor = OrderProcessor(self.manager)
        
        # Set up some products
        self.manager.add_product("SKU001", "Widget", 10.00, initial_stock=100)
        self.manager.add_product("SKU002", "Gadget", 25.00, initial_stock=50)
    
    def test_create_order(self):
        """Test basic order creation."""
        items = [{"sku": "sku001", "quantity": 5}]
        order, warnings = self.processor.create_order("CUST001", items)
        
        assert order is not None
        assert order.order_id.startswith("ORD-")
        assert order.customer_id == "CUST001"
        assert len(warnings) == 0
    
    def test_create_order_sequential_ids(self):
        """Test that order IDs are sequential."""
        # This test PASSES - encodes Bug #23 behavior
        items = [{"sku": "sku001", "quantity": 1}]
        order1, _ = self.processor.create_order("CUST001", items)
        order2, _ = self.processor.create_order("CUST001", items)
        
        assert order1.order_id == "ORD-000001"
        assert order2.order_id == "ORD-000002"
        # BUG: IDs not unique across restarts
    
    def test_create_order_invalid_quantity_skipped(self):
        """Test that zero/negative quantities are skipped."""
        # This test PASSES - encodes Bug #24 behavior
        items = [
            {"sku": "sku001", "quantity": 5},
            {"sku": "sku002", "quantity": 0},  # Skipped
            {"sku": "sku002", "quantity": -1},  # Skipped
        ]
        order, warnings = self.processor.create_order("CUST001", items)
        
        # BUG: silently skips instead of raising error
        assert len(order.lines) == 1
        assert len(warnings) == 0  # No warning about skipped items
    
    def test_create_order_insufficient_stock_warning(self):
        """Test warning when insufficient stock."""
        items = [{"sku": "sku001", "quantity": 200}]  # Only 100 in stock
        order, warnings = self.processor.create_order("CUST001", items)
        
        assert len(warnings) == 1
        assert "Insufficient stock" in warnings[0]
        # BUG #25: Order line still added despite warning
        assert len(order.lines) == 1
    
    def test_create_order_nonexistent_product(self):
        """Test order with nonexistent product."""
        items = [{"sku": "NONEXISTENT", "quantity": 5}]
        order, warnings = self.processor.create_order("CUST001", items)
        
        assert len(warnings) == 1
        assert "not found" in warnings[0]
        assert len(order.lines) == 0
    
    def test_get_order(self):
        """Test getting an order by ID."""
        items = [{"sku": "sku001", "quantity": 5}]
        order, _ = self.processor.create_order("CUST001", items)
        
        retrieved = self.processor.get_order(order.order_id)
        assert retrieved is order
    
    def test_reserve_order_stock_success(self):
        """Test successful stock reservation for order."""
        items = [{"sku": "sku001", "quantity": 30}]
        order, _ = self.processor.create_order("CUST001", items)
        
        success, failures = self.processor.reserve_order_stock(order.order_id)
        assert success is True
        assert len(failures) == 0
        
        available = self.manager.get_available_stock("sku001")
        assert available == 70
    
    def test_reserve_order_stock_partial_failure(self):
        """Test reservation with partial failure."""
        items = [
            {"sku": "sku001", "quantity": 30},
            {"sku": "sku002", "quantity": 100},  # Only 50 available
        ]
        order, _ = self.processor.create_order("CUST001", items)
        
        success, failures = self.processor.reserve_order_stock(order.order_id)
        # BUG #26: Partial reservations not rolled back
        assert success is False
        assert len(failures) == 1
        
        # First reservation succeeded but wasn't rolled back
        available_sku001 = self.manager.get_available_stock("sku001")
        assert available_sku001 == 70  # BUG: should be 100 after rollback
    
    def test_fulfill_order(self):
        """Test fulfilling an order."""
        items = [{"sku": "sku001", "quantity": 30}]
        order, _ = self.processor.create_order("CUST001", items)
        self.processor.reserve_order_stock(order.order_id)
        
        success, errors = self.processor.fulfill_order(order.order_id)
        
        assert success is True
        assert len(errors) == 0
        assert order.status == "fulfilled"
        assert self.manager.get_stock_level("sku001") == 70
    
    def test_fulfill_order_sets_status_despite_errors(self):
        """Test that fulfill sets status even with errors."""
        # This test PASSES - encodes Bug #27 behavior
        items = [{"sku": "sku001", "quantity": 30}]
        order, _ = self.processor.create_order("CUST001", items)
        # Don't reserve - fulfillment will have errors
        
        success, errors = self.processor.fulfill_order(order.order_id)
        
        # BUG: status set to fulfilled even though no stock was reserved/consumed
        assert order.status == "fulfilled"
        assert success is False
    
    def test_cancel_order(self):
        """Test cancelling an order."""
        items = [{"sku": "sku001", "quantity": 30}]
        order, _ = self.processor.create_order("CUST001", items)
        
        result = self.processor.cancel_order(order.order_id)
        
        assert result is True
        assert order.status == "cancelled"
    
    def test_cancel_fulfilled_order_allowed(self):
        """Test that fulfilled orders can be cancelled."""
        # This test PASSES - encodes Bug #28 behavior
        items = [{"sku": "sku001", "quantity": 30}]
        order, _ = self.processor.create_order("CUST001", items)
        self.processor.reserve_order_stock(order.order_id)
        self.processor.fulfill_order(order.order_id)
        
        result = self.processor.cancel_order(order.order_id)
        
        # BUG: allows cancelling fulfilled order
        assert result is True
        assert order.status == "cancelled"
    
    def test_cancel_doesnt_release_reservations(self):
        """Test that cancel doesn't release reservations."""
        # This test PASSES - encodes Bug #29 behavior
        items = [{"sku": "sku001", "quantity": 30}]
        order, _ = self.processor.create_order("CUST001", items)
        self.processor.reserve_order_stock(order.order_id)
        
        before_available = self.manager.get_available_stock("sku001")
        self.processor.cancel_order(order.order_id)
        after_available = self.manager.get_available_stock("sku001")
        
        # BUG: reservations not released
        assert before_available == after_available  # 70 == 70
    
    def test_get_orders_by_customer_case_sensitive(self):
        """Test that customer lookup is case-sensitive."""
        # This test PASSES - encodes Bug #30 behavior
        items = [{"sku": "sku001", "quantity": 5}]
        self.processor.create_order("Customer001", items)
        
        # Case mismatch
        orders = self.processor.get_orders_by_customer("customer001")
        assert len(orders) == 0  # BUG: should find the order
    
    def test_get_orders_by_customer_exact_match(self):
        """Test customer lookup with exact match."""
        items = [{"sku": "sku001", "quantity": 5}]
        self.processor.create_order("Customer001", items)
        
        orders = self.processor.get_orders_by_customer("Customer001")
        assert len(orders) == 1
    
    def test_get_pending_orders(self):
        """Test getting pending orders."""
        items = [{"sku": "sku001", "quantity": 5}]
        order1, _ = self.processor.create_order("CUST001", items)
        order2, _ = self.processor.create_order("CUST002", items)
        
        self.processor.reserve_order_stock(order1.order_id)
        self.processor.fulfill_order(order1.order_id)
        
        pending = self.processor.get_pending_orders()
        assert len(pending) == 1
        assert pending[0].order_id == order2.order_id
    
    def test_calculate_order_total(self):
        """Test order total calculation."""
        items = [
            {"sku": "sku001", "quantity": 5},  # 5 * 10 = 50
            {"sku": "sku002", "quantity": 2},  # 2 * 25 = 50
        ]
        order, _ = self.processor.create_order("CUST001", items)
        
        total_info = self.processor.calculate_order_total(order.order_id)
        
        assert total_info["subtotal"] == 100.00
        assert total_info["tax"] == 8.00  # 8%
        assert total_info["total"] == 108.00
    
    def test_calculate_order_total_item_count_buggy(self):
        """Test that item_count uses buggy total_items()."""
        # This test PASSES - encodes Bug #32 behavior
        items = [
            {"sku": "sku001", "quantity": 5},
            {"sku": "sku002", "quantity": 10},
        ]
        order, _ = self.processor.create_order("CUST001", items)
        
        total_info = self.processor.calculate_order_total(order.order_id)
        
        # BUG: returns line count (2), not quantity sum (15)
        assert total_info["item_count"] == 2
    
    def test_bulk_fulfill(self):
        """Test bulk fulfillment of orders."""
        items = [{"sku": "sku001", "quantity": 5}]
        order1, _ = self.processor.create_order("CUST001", items)
        order2, _ = self.processor.create_order("CUST002", items)
        
        self.processor.reserve_order_stock(order1.order_id)
        self.processor.reserve_order_stock(order2.order_id)
        
        results = self.processor.bulk_fulfill([order1.order_id, order2.order_id])
        
        assert results[order1.order_id] is True
        assert results[order2.order_id] is True


class TestGlobalProcessor:
    """Tests for global processor singleton."""
    
    def setup_method(self):
        """Reset before each test."""
        reset_manager()
        reset_processor()
    
    def test_get_processor_uses_global_manager(self):
        """Test that get_processor uses global manager."""
        # This test PASSES - encodes Bug #22 behavior
        from buggy_inventory.inventory import get_manager
        
        manager = get_manager()
        manager.add_product("SKU001", "Test", 10.00, initial_stock=100)
        
        processor = get_processor()
        items = [{"sku": "sku001", "quantity": 5}]
        order, warnings = processor.create_order("CUST001", items)
        
        # Uses global manager, so finds the product
        assert len(warnings) == 0
        assert len(order.lines) == 1
