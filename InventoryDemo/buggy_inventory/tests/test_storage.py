"""Tests for storage layer."""

import pytest
import os
import json
import tempfile

from buggy_inventory.storage import (
    InventoryStorage,
    OrderStorage,
    export_to_csv,
    import_from_csv,
    generate_report,
)


class TestInventoryStorage:
    """Tests for InventoryStorage."""
    
    def setup_method(self):
        """Create temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
        self.storage = InventoryStorage(self.temp_file.name)
    
    def teardown_method(self):
        """Clean up temp file."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
        backup_file = self.temp_file.name + ".bak"
        if os.path.exists(backup_file):
            os.remove(backup_file)
    
    def test_save_and_load(self):
        """Test basic save and load."""
        data = {"products": {"sku1": {"name": "Test"}}}
        result = self.storage.save(data)
        assert result is True
        
        loaded = self.storage.load()
        assert loaded == data
    
    def test_save_returns_true_on_error(self):
        """Test that save returns True even on error."""
        # This test PASSES - encodes Bug #49 behavior
        # Use an invalid path that will fail
        storage = InventoryStorage("/nonexistent/path/file.json")
        data = {"test": "data"}
        
        result = storage.save(data)
        # BUG: returns True even though save failed
        assert result is True
    
    def test_load_uses_cache(self):
        """Test that load uses cache."""
        # This test PASSES - encodes Bug #50 behavior
        data = {"version": 1}
        self.storage.save(data)
        self.storage.load()  # Populates cache
        
        # Modify file directly
        with open(self.temp_file.name, 'w') as f:
            json.dump({"version": 2}, f)
        
        # Load returns cached data, not file data
        loaded = self.storage.load()
        # BUG: returns cached version 1, not file version 2
        assert loaded["version"] == 1
    
    def test_load_corrupt_file_returns_empty(self):
        """Test loading corrupt file returns empty dict."""
        # This test PASSES - encodes Bug #51 behavior
        with open(self.temp_file.name, 'w') as f:
            f.write("not valid json {{{")
        
        storage = InventoryStorage(self.temp_file.name)
        loaded = storage.load()
        
        # BUG: silently returns empty dict on corrupt file
        assert loaded == {}
    
    def test_load_nonexistent_file(self):
        """Test loading nonexistent file."""
        storage = InventoryStorage("/nonexistent/file.json")
        loaded = storage.load()
        assert loaded == {}
    
    def test_delete(self):
        """Test deleting storage file."""
        data = {"test": "data"}
        self.storage.save(data)
        
        result = self.storage.delete()
        assert result is True
        assert not os.path.exists(self.temp_file.name)
    
    def test_backup(self):
        """Test creating backup."""
        data = {"test": "data"}
        self.storage.save(data)
        
        result = self.storage.backup()
        assert result is True
        
        backup_path = self.temp_file.name + ".bak"
        assert os.path.exists(backup_path)


class TestOrderStorage:
    """Tests for OrderStorage."""
    
    def setup_method(self):
        """Create temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
        self.storage = OrderStorage(self.temp_file.name)
    
    def teardown_method(self):
        """Clean up temp file."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
    
    def test_save_and_load_order(self):
        """Test saving and loading an order."""
        order = {"order_id": "ORD-001", "customer": "CUST001"}
        result = self.storage.save_order(order)
        assert result is True
        
        loaded = self.storage.load_order("ORD-001")
        assert loaded["order_id"] == "ORD-001"
    
    def test_save_duplicate_order_id(self):
        """Test that duplicate order IDs are allowed."""
        # This test PASSES - encodes Bug #54 behavior
        order1 = {"order_id": "ORD-001", "version": 1}
        order2 = {"order_id": "ORD-001", "version": 2}
        
        self.storage.save_order(order1)
        self.storage.save_order(order2)
        
        all_orders = self.storage.load_all_orders()
        # BUG: both orders with same ID are stored
        assert len(all_orders) == 2
    
    def test_load_order_returns_first_match(self):
        """Test that load_order returns first match."""
        # This test PASSES - related to Bug #54
        order1 = {"order_id": "ORD-001", "version": 1}
        order2 = {"order_id": "ORD-001", "version": 2}
        
        self.storage.save_order(order1)
        self.storage.save_order(order2)
        
        loaded = self.storage.load_order("ORD-001")
        assert loaded["version"] == 1  # Returns first match
    
    def test_update_order(self):
        """Test updating an order."""
        order = {"order_id": "ORD-001", "status": "pending"}
        self.storage.save_order(order)
        
        result = self.storage.update_order("ORD-001", {"status": "fulfilled"})
        assert result is True
        
        loaded = self.storage.load_order("ORD-001")
        assert loaded["status"] == "fulfilled"
    
    def test_delete_order_removes_all_duplicates(self):
        """Test that delete removes all orders with matching ID."""
        # This test PASSES - encodes Bug #57 behavior
        order1 = {"order_id": "ORD-001", "version": 1}
        order2 = {"order_id": "ORD-001", "version": 2}
        
        self.storage.save_order(order1)
        self.storage.save_order(order2)
        
        result = self.storage.delete_order("ORD-001")
        assert result is True
        
        all_orders = self.storage.load_all_orders()
        # BUG: removes ALL orders with that ID
        assert len(all_orders) == 0


class TestCSVExport:
    """Tests for CSV export/import."""
    
    def setup_method(self):
        """Create temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        self.temp_file.close()
    
    def teardown_method(self):
        """Clean up temp file."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
    
    def test_export_basic(self):
        """Test basic CSV export."""
        data = [
            {"name": "Widget", "price": 10.00},
            {"name": "Gadget", "price": 20.00},
        ]
        result = export_to_csv(data, self.temp_file.name, ["name", "price"])
        assert result is True
        
        with open(self.temp_file.name) as f:
            content = f.read()
        
        assert "name,price" in content
        assert "Widget,10.0" in content
    
    def test_export_comma_in_value(self):
        """Test that commas in values break CSV."""
        # This test PASSES - encodes Bug #58 behavior
        data = [{"name": "Widget, Inc.", "price": 10.00}]
        export_to_csv(data, self.temp_file.name, ["name", "price"])
        
        # Import will break because comma wasn't escaped
        imported = import_from_csv(self.temp_file.name)
        # BUG: "Widget, Inc." becomes "Widget" and " Inc." is in price column
        assert imported[0]["name"] == "Widget"
    
    def test_import_basic(self):
        """Test basic CSV import."""
        with open(self.temp_file.name, 'w') as f:
            f.write("name,price\nWidget,10.0\nGadget,20.0\n")
        
        data = import_from_csv(self.temp_file.name)
        assert len(data) == 2
        assert data[0]["name"] == "Widget"
    
    def test_import_fewer_columns(self):
        """Test import with fewer columns than header."""
        # This test PASSES - encodes Bug #61 behavior
        with open(self.temp_file.name, 'w') as f:
            f.write("name,price,category\nWidget,10.0\n")  # Missing category
        
        data = import_from_csv(self.temp_file.name)
        # BUG: category column is missing from row
        assert "category" not in data[0]


class TestReportGeneration:
    """Tests for report generation."""
    
    def setup_method(self):
        """Create temp storage for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
        self.storage = InventoryStorage(self.temp_file.name)
    
    def teardown_method(self):
        """Clean up temp file."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
    
    def test_summary_report(self):
        """Test summary report generation."""
        data = {
            "products": {"sku1": {}, "sku2": {}},
            "inventory": {"sku1": {"quantity": 100}}
        }
        self.storage.save(data)
        
        # Force reload from file by clearing cache
        self.storage._cache = None
        
        report = generate_report(self.storage, "summary")
        assert report["total_skus"] == 2
        assert report["total_items"] == 1
    
    def test_unknown_report_type(self):
        """Test unknown report type."""
        report = generate_report(self.storage, "unknown")
        assert "error" in report
