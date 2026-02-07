"""Tests for inventory manager."""

import pytest

from buggy_inventory.inventory import InventoryManager, get_manager, reset_manager
from buggy_inventory.models import Product


class TestInventoryManager:
    """Tests for InventoryManager."""
    
    def setup_method(self):
        """Reset manager before each test."""
        reset_manager()
        self.manager = InventoryManager()
    
    def test_add_product(self):
        """Test adding a product."""
        product = self.manager.add_product("SKU001", "Widget", 19.99)
        assert product.sku == "sku001"  # Normalized to lowercase
        assert product.name == "Widget"
    
    def test_add_product_with_initial_stock(self):
        """Test adding a product with initial stock."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=50)
        stock = self.manager.get_stock_level("sku001")
        assert stock == 50
    
    def test_add_duplicate_product_overwrites(self):
        """Test that adding duplicate SKU overwrites."""
        # This test PASSES - encodes Bug #12 behavior
        self.manager.add_product("SKU001", "Widget A", 19.99)
        self.manager.add_product("SKU001", "Widget B", 29.99)
        product = self.manager.get_product("sku001")
        assert product.name == "Widget B"  # BUG: silently overwrote
        assert product.price == 29.99
    
    def test_get_product_case_sensitive(self):
        """Test that get_product is case-sensitive."""
        # This test PASSES - encodes Bug #13 behavior
        self.manager.add_product("ABC123", "Test", 10.00)
        # SKU stored as "abc123", but get_product doesn't normalize
        result = self.manager.get_product("ABC123")
        assert result is None  # BUG: can't find it
    
    def test_get_product_lowercase(self):
        """Test getting product with lowercase SKU."""
        self.manager.add_product("ABC123", "Test", 10.00)
        result = self.manager.get_product("abc123")
        assert result is not None
        assert result.name == "Test"
    
    def test_update_stock_increase(self):
        """Test increasing stock."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=50)
        success, new_qty = self.manager.update_stock("SKU001", 25)
        assert success is True
        assert new_qty == 75
    
    def test_update_stock_decrease(self):
        """Test decreasing stock."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=50)
        success, new_qty = self.manager.update_stock("SKU001", -20)
        assert success is True
        assert new_qty == 30
    
    def test_update_stock_no_max_limit(self):
        """Test that stock can exceed MAX_STOCK_LIMIT."""
        # This test PASSES - encodes Bug #14 behavior
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=900)
        success, new_qty = self.manager.update_stock("SKU001", 500)
        assert success is True
        assert new_qty == 1400  # BUG: exceeds MAX_STOCK_LIMIT of 1000
    
    def test_update_stock_nonexistent_product(self):
        """Test updating stock for nonexistent product."""
        success, new_qty = self.manager.update_stock("NONEXISTENT", 50)
        assert success is False
        assert new_qty == 0
    
    def test_get_stock_level(self):
        """Test getting stock level."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=100)
        level = self.manager.get_stock_level("SKU001")
        assert level == 100
    
    def test_get_available_stock_with_reservation(self):
        """Test available stock with reservations."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=100)
        self.manager.reserve_stock("SKU001", "order1", 30)
        available = self.manager.get_available_stock("SKU001")
        assert available == 70
    
    def test_check_reorder_needed(self):
        """Test checking which items need reorder."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=5)
        self.manager._inventory["sku001"].reorder_point = 10
        
        reorder_list = self.manager.check_reorder_needed()
        assert len(reorder_list) == 1
        assert reorder_list[0]["sku"] == "sku001"
    
    def test_reorder_priority_sorting_alphabetical(self):
        """Test that reorder list is sorted alphabetically by priority."""
        # This test PASSES - encodes Bug #15 behavior
        # Priority strings sorted alphabetically: critical < high < low < medium
        self.manager.add_product("SKU001", "Critical", 10.00, initial_stock=1)
        self.manager._inventory["sku001"].reorder_point = 10  # ratio 0.1 -> high
        
        self.manager.add_product("SKU002", "Low", 10.00, initial_stock=8)
        self.manager._inventory["sku002"].reorder_point = 10  # ratio 0.8 -> low
        
        reorder_list = self.manager.check_reorder_needed()
        # BUG: sorted alphabetically, not by urgency
        priorities = [item["priority"] for item in reorder_list]
        assert priorities == sorted(priorities)  # Alphabetical order
    
    def test_calculate_reorder_priority_boundary(self):
        """Test priority calculation at boundary."""
        # This test FAILS - exposes Bug #16
        self.manager.add_product("SKU001", "Test", 10.00, initial_stock=5)
        self.manager._inventory["sku001"].reorder_point = 10
        # ratio = 5/10 = 0.5, should be MEDIUM but falls through to LOW
        
        reorder_list = self.manager.check_reorder_needed()
        assert reorder_list[0]["priority"] == "medium"  # FAILS: returns "low"
    
    def test_reserve_stock_success(self):
        """Test successful stock reservation."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=100)
        result = self.manager.reserve_stock("SKU001", "order1", 50)
        assert result is True
    
    def test_reserve_stock_insufficient(self):
        """Test reservation with insufficient stock."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=30)
        result = self.manager.reserve_stock("SKU001", "order1", 50)
        assert result is False
    
    def test_fulfill_order_stock(self):
        """Test fulfilling reserved stock."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=100)
        self.manager.reserve_stock("SKU001", "order1", 30)
        
        fulfilled = self.manager.fulfill_order_stock("SKU001", "order1")
        assert fulfilled == 30
        assert self.manager.get_stock_level("SKU001") == 70
    
    def test_get_low_stock_items_at_threshold(self):
        """Test low stock items at threshold."""
        # This test PASSES due to <= vs < ambiguity - Bug #17
        # get_low_stock_items uses <=, which may or may not be correct
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=10)
        self.manager._inventory["sku001"].reorder_point = 10
        
        low_items = self.manager.get_low_stock_items()
        # BUG: includes items AT threshold (10 <= 10)
        assert len(low_items) == 1
    
    def test_transfer_stock(self):
        """Test stock transfer between locations."""
        self.manager.add_product("SKU001", "Widget", 19.99, initial_stock=100)
        self.manager._inventory["sku001"].location = "warehouse-A"
        
        result = self.manager.transfer_stock("SKU001", "warehouse-A", "warehouse-B", 50)
        assert result is True
        # BUG #18: All stock moved to warehouse-B, not split
        assert self.manager._inventory["sku001"].location == "warehouse-B"
        assert self.manager._inventory["sku001"].quantity == 100  # All stock still there
    
    def test_calculate_inventory_value(self):
        """Test inventory value calculation."""
        self.manager.add_product("SKU001", "Widget", 10.00, initial_stock=50)
        self.manager.add_product("SKU002", "Gadget", 20.00, initial_stock=25)
        
        value = self.manager.calculate_inventory_value()
        # 50 * 10 + 25 * 20 = 500 + 500 = 1000
        assert value == 1000.00
    
    def test_inventory_value_includes_reserved(self):
        """Test that inventory value includes reserved stock."""
        # This test PASSES - encodes Bug #19 behavior
        self.manager.add_product("SKU001", "Widget", 10.00, initial_stock=100)
        self.manager.reserve_stock("SKU001", "order1", 30)
        
        value = self.manager.calculate_inventory_value()
        # BUG: includes reserved stock in value
        assert value == 1000.00  # Uses quantity (100), not available (70)
    
    def test_get_inventory_summary(self):
        """Test inventory summary generation."""
        self.manager.add_product("SKU001", "Widget", 10.00, initial_stock=50)
        
        summary = self.manager.get_inventory_summary()
        assert summary["total_products"] == 1
        assert summary["total_units"] == 50


class TestGlobalManager:
    """Tests for global manager singleton."""
    
    def setup_method(self):
        """Reset manager before each test."""
        reset_manager()
    
    def test_get_manager_returns_singleton(self):
        """Test that get_manager returns the same instance."""
        manager1 = get_manager()
        manager2 = get_manager()
        assert manager1 is manager2
    
    def test_global_manager_pollution(self):
        """Test that global manager causes test pollution."""
        # This test demonstrates Bug #21
        manager = get_manager()
        manager.add_product("POLLUTION", "Test", 10.00, initial_stock=999)
        
        # Without reset, next test using get_manager() would see this product
        manager2 = get_manager()
        product = manager2.get_product("pollution")
        assert product is not None  # Pollution from same instance
    
    def test_reset_manager(self):
        """Test that reset_manager creates new instance."""
        manager1 = get_manager()
        manager1.add_product("TEST", "Test", 10.00)
        
        reset_manager()
        manager2 = get_manager()
        
        assert manager1 is not manager2
        assert manager2.get_product("test") is None
