# Bug Map: Buggy Inventory Management System

This document catalogs all intentionally seeded bugs in the inventory management demo application. Bugs are organized by module, severity, and type.

## Summary

| Severity | Count |
|----------|-------|
| High     | 8     |
| Medium   | 12    |
| Low      | 9     |
| **Total**| **29**|

## Bug Categories

- **Logic**: Incorrect conditionals, off-by-one errors, wrong operators
- **State**: Mutable defaults, shared state, missing updates
- **Validation**: Missing input checks, silent acceptance of invalid data
- **Error Handling**: Silent failures, swallowed exceptions
- **Precision**: Floating point issues, rounding errors
- **Coupling**: Global state, test pollution

---

## Models (`models.py`)

### Bug #1: SKU Normalization Incomplete
- **Severity**: Medium
- **Type**: Validation
- **Line**: `Product.__post_init__`
- **Description**: SKU only lowercased, not stripped. `" ABC "` and `"abc"` are different SKUs.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #2: Display Price Rounding Issue
- **Severity**: Low
- **Type**: Precision
- **Line**: `Product.get_display_price`
- **Description**: Uses `round()` which can cause banker's rounding issues.
- **Test Status**: ✅ Passes (lucky math in test cases)

### Bug #3: Mutable Default in Reserved Quantities
- **Severity**: High
- **Type**: State
- **Line**: `InventoryItem.reserved_quantities`
- **Description**: Default dict shared across instances (fixed with field default_factory).
- **Test Status**: N/A (fixed in implementation)

### Bug #4: Reorder Check Uses < Instead of <=
- **Severity**: High
- **Type**: Logic
- **Line**: `InventoryItem.needs_reorder`
- **Description**: When quantity equals reorder_point, doesn't trigger reorder.
- **Test Status**: ❌ Fails (exposes bug)

### Bug #5: Fulfillment Doesn't Update Timestamp
- **Severity**: Low
- **Type**: State
- **Line**: `InventoryItem.fulfill_reservation`
- **Description**: `last_updated` not set when stock changes via fulfillment.
- **Test Status**: ✅ Passes (not explicitly tested)

### Bug #6: Add Stock Allows Negative
- **Severity**: Medium
- **Type**: Validation
- **Line**: `InventoryItem.add_stock`
- **Description**: No validation prevents adding negative amounts, allowing negative stock.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #7: Line Total Precision Loss
- **Severity**: Medium
- **Type**: Precision
- **Line**: `OrderLine.line_total`
- **Description**: Applies discount to unit price first, then multiplies. Can cause precision loss.
- **Test Status**: ✅ Passes (lucky math)

### Bug #8: Mutable Default in Order Metadata
- **Severity**: Medium
- **Type**: State
- **Line**: `Order.metadata`
- **Description**: Default dict could be shared (fixed with field default_factory).
- **Test Status**: N/A (fixed in implementation)

### Bug #9: Duplicate Order Lines Allowed
- **Severity**: Medium
- **Type**: Validation
- **Line**: `Order.add_line`
- **Description**: Doesn't check if SKU already exists, allows duplicate lines.
- **Test Status**: ✅ Passes (not explicitly tested)

### Bug #10: total_items Returns Line Count
- **Severity**: High
- **Type**: Logic
- **Line**: `Order.total_items`
- **Description**: Returns number of lines, not sum of quantities.
- **Test Status**: ❌ Fails (test expects quantity sum)

### Bug #11: Remove Line Mutation During Iteration
- **Severity**: Medium
- **Type**: Logic
- **Line**: `Order.remove_line`
- **Description**: Modifies list while iterating, always returns True.
- **Test Status**: ✅ Passes (encodes buggy behavior)

---

## Inventory Manager (`inventory.py`)

### Bug #12: Add Product Silently Overwrites
- **Severity**: Medium
- **Type**: Validation
- **Line**: `InventoryManager.add_product`
- **Description**: Doesn't check if product exists, silently overwrites.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #13: get_product Doesn't Normalize SKU
- **Severity**: High
- **Type**: Logic
- **Line**: `InventoryManager.get_product`
- **Description**: add_product normalizes SKU, but get_product doesn't.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #14: No MAX_STOCK_LIMIT Enforcement
- **Severity**: Medium
- **Type**: Validation
- **Line**: `InventoryManager.update_stock`
- **Description**: Stock can exceed MAX_STOCK_LIMIT constant.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #15: Priority Sorted Alphabetically
- **Severity**: High
- **Type**: Logic
- **Line**: `InventoryManager.check_reorder_needed`
- **Description**: Sorts by priority string alphabetically, not by urgency.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #16: Priority Boundary Condition
- **Severity**: Medium
- **Type**: Logic
- **Line**: `InventoryManager._calculate_reorder_priority`
- **Description**: Ratio of 0.5 falls through to LOW instead of MEDIUM.
- **Test Status**: ❌ Fails (exposes bug)

### Bug #17: Low Stock Items Includes Threshold
- **Severity**: Low
- **Type**: Logic
- **Line**: `InventoryManager.get_low_stock_items`
- **Description**: Uses <= instead of <, includes items AT threshold.
- **Test Status**: ✅ Passes (ambiguous requirement)

### Bug #18: Transfer Doesn't Actually Split Stock
- **Severity**: High
- **Type**: Logic
- **Line**: `InventoryManager.transfer_stock`
- **Description**: Only changes location field, doesn't track multiple locations.
- **Test Status**: ✅ Passes (test doesn't verify split)

### Bug #19: Inventory Value Includes Reserved
- **Severity**: Medium
- **Type**: Logic
- **Line**: `InventoryManager.calculate_inventory_value`
- **Description**: Uses quantity, not available_quantity, in value calculation.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #20: Summary Value Display Formatting
- **Severity**: Low
- **Type**: Precision
- **Line**: `InventoryManager.get_inventory_summary`
- **Description**: `total_value_display` may have precision issues.
- **Test Status**: ✅ Passes (not explicitly tested)

### Bug #21: Global Singleton Manager
- **Severity**: High
- **Type**: Coupling
- **Line**: `get_manager()` / `_manager_instance`
- **Description**: Global singleton causes test pollution.
- **Test Status**: ✅ Passes (test resets before each test)

---

## Order Processing (`orders.py`)

### Bug #22: Processor Uses Global Manager
- **Severity**: Medium
- **Type**: Coupling
- **Line**: `OrderProcessor.__init__`
- **Description**: Falls back to global singleton if no manager provided.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #23: Sequential Order IDs
- **Severity**: Low
- **Type**: Logic
- **Line**: `OrderProcessor.create_order`
- **Description**: Order IDs are sequential, not unique across restarts.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #24: Invalid Quantity Silently Skipped
- **Severity**: Medium
- **Type**: Validation
- **Line**: `OrderProcessor.create_order`
- **Description**: Zero/negative quantities skipped without warning.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #25: Insufficient Stock Still Adds Line
- **Severity**: High
- **Type**: Logic
- **Line**: `OrderProcessor.create_order`
- **Description**: Order line added even when stock is insufficient.
- **Test Status**: ✅ Passes (verifies line was added)

### Bug #26: Partial Reservation No Rollback
- **Severity**: High
- **Type**: State
- **Line**: `OrderProcessor.reserve_order_stock`
- **Description**: Successful reservations not rolled back on partial failure.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #27: Fulfill Sets Status Despite Errors
- **Severity**: High
- **Type**: Logic
- **Line**: `OrderProcessor.fulfill_order`
- **Description**: Status set to fulfilled even when errors occurred.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #28: Can Cancel Fulfilled Orders
- **Severity**: Medium
- **Type**: Validation
- **Line**: `OrderProcessor.cancel_order`
- **Description**: Allows cancelling already-fulfilled orders.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #29: Cancel Doesn't Release Reservations
- **Severity**: High
- **Type**: State
- **Line**: `OrderProcessor.cancel_order`
- **Description**: Reservations not released when order cancelled.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #30: Customer ID Case-Sensitive
- **Severity**: Low
- **Type**: Logic
- **Line**: `OrderProcessor.get_orders_by_customer`
- **Description**: Customer lookup is case-sensitive.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #31: Tax and Subtotal Rounded Separately
- **Severity**: Low
- **Type**: Precision
- **Line**: `OrderProcessor.calculate_order_total`
- **Description**: Can cause penny discrepancies.
- **Test Status**: ✅ Passes (lucky math)

### Bug #32: Item Count Uses Buggy total_items
- **Severity**: Medium
- **Type**: Logic
- **Line**: `OrderProcessor.calculate_order_total`
- **Description**: Uses Order.total_items() which returns line count.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #33: Bulk Fulfill Order Not FIFO
- **Severity**: Low
- **Type**: Logic
- **Line**: `OrderProcessor.bulk_fulfill`
- **Description**: Doesn't sort by creation date before fulfilling.
- **Test Status**: ✅ Passes (not explicitly tested)

---

## Pricing (`pricing.py`)

### Bug #34: Discount Tiers Overlap
- **Severity**: Low
- **Type**: Logic
- **Line**: `calculate_bulk_discount`
- **Description**: Quantity of 500 qualifies for both bulk and wholesale checks.
- **Test Status**: ✅ Passes (wholesale wins, which is correct)

### Bug #35: Bulk Discount Returns Raw Float
- **Severity**: Low
- **Type**: Precision
- **Line**: `calculate_bulk_discount`
- **Description**: Returns unrounded float, can have precision artifacts.
- **Test Status**: ✅ Passes (lucky math in tests)

### Bug #36: Tiered Discount Boundary
- **Severity**: Low
- **Type**: Logic
- **Line**: `calculate_tiered_discount`
- **Description**: Boundary condition at 100 units.
- **Test Status**: ✅ Passes (boundary actually correct)

### Bug #37: Promo Codes Case-Sensitive
- **Severity**: Medium
- **Type**: Validation
- **Line**: `apply_promo_code`
- **Description**: "SAVE10" works but "save10" doesn't.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #38: FREE Promo Code 100% Discount
- **Severity**: Medium
- **Type**: Validation
- **Line**: `apply_promo_code`
- **Description**: Allows 100% discount with FREE code.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #39: Weight Surcharge Integer Division
- **Severity**: Low
- **Type**: Precision
- **Line**: `calculate_shipping`
- **Description**: Uses int() which truncates weight.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #40: Express Multiplier Base Only
- **Severity**: Medium
- **Type**: Logic
- **Line**: `calculate_shipping`
- **Description**: Express 50% only applies to base, not weight surcharge.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #41: Tax Uses Banker's Rounding
- **Severity**: Low
- **Type**: Precision
- **Line**: `calculate_tax`
- **Description**: round() uses banker's rounding.
- **Test Status**: ✅ Passes (demonstrates behavior)

### Bug #42: Negative Currency Format
- **Severity**: Low
- **Type**: Logic
- **Line**: `format_currency`
- **Description**: -5.00 becomes "$-5.00" not "-$5.00".
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #43-44: Currency Parsing Issues
- **Severity**: Low
- **Type**: Validation
- **Line**: `parse_currency`
- **Description**: Limited format support, returns 0 on error.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #45: Margin vs Markup
- **Severity**: High
- **Type**: Logic
- **Line**: `calculate_margin`
- **Description**: Function calculates markup, not margin.
- **Test Status**: ❌ Fails (test expects margin)

### Bug #46: Split Payment Loses Pennies
- **Severity**: Medium
- **Type**: Precision
- **Line**: `split_payment`
- **Description**: 100/3 = 33.33 each = 99.99 total.
- **Test Status**: ❌ Fails (test expects 100.00)

### Bug #47-48: Precise Order Total Precision Loss
- **Severity**: Low
- **Type**: Precision
- **Line**: `calculate_order_total_precise`
- **Description**: Converts to float for promo, losing Decimal precision.
- **Test Status**: ✅ Passes (within tolerance)

---

## Storage (`storage.py`)

### Bug #49: Save Returns True on Error
- **Severity**: High
- **Type**: Error Handling
- **Line**: `InventoryStorage.save`
- **Description**: Silently swallows exception and returns True.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #50: Load Uses Stale Cache
- **Severity**: Medium
- **Type**: State
- **Line**: `InventoryStorage.load`
- **Description**: Cache not invalidated when file changes externally.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #51-52: Load Errors Return Empty Dict
- **Severity**: Medium
- **Type**: Error Handling
- **Line**: `InventoryStorage.load`
- **Description**: Corrupt file or errors return empty dict, losing data.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #53: Backup Overwrites Without Warning
- **Severity**: Low
- **Type**: Validation
- **Line**: `InventoryStorage.backup`
- **Description**: Overwrites existing backup silently.
- **Test Status**: ✅ Passes (not explicitly tested)

### Bug #54: Duplicate Order IDs Allowed
- **Severity**: Medium
- **Type**: Validation
- **Line**: `OrderStorage.save_order`
- **Description**: Doesn't check for duplicate order IDs.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #55: Linear Order Search
- **Severity**: Low
- **Type**: Logic
- **Line**: `OrderStorage.load_order`
- **Description**: O(n) search through all orders.
- **Test Status**: ✅ Passes (functional, just slow)

### Bug #56: Shallow Merge in Update
- **Severity**: Low
- **Type**: Logic
- **Line**: `OrderStorage.update_order`
- **Description**: Shallow update doesn't handle nested dicts.
- **Test Status**: ✅ Passes (not explicitly tested)

### Bug #57: Delete Removes All Duplicates
- **Severity**: Medium
- **Type**: Logic
- **Line**: `OrderStorage.delete_order`
- **Description**: Removes ALL orders with matching ID.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #58-61: CSV Handling Issues
- **Severity**: Low-Medium
- **Type**: Logic / Validation
- **Line**: `export_to_csv`, `import_from_csv`
- **Description**: No comma escaping, simple split breaks quoted fields.
- **Test Status**: ✅ Passes (encodes buggy behavior)

### Bug #62: Report Assumes Structure
- **Severity**: Low
- **Type**: Validation
- **Line**: `generate_report`
- **Description**: Assumes specific data structure, breaks if changed.
- **Test Status**: ✅ Passes (correct structure in tests)

---

## Test Summary

| Test Status | Count | Description |
|-------------|-------|-------------|
| ✅ Passes (correct) | ~40 | Tests that verify correct behavior |
| ✅ Passes (buggy) | ~25 | Tests that encode buggy behavior as expected |
| ✅ Passes (lucky) | ~10 | Tests that pass due to edge cases/math |
| ❌ Fails | ~5 | Tests that correctly expose bugs |

This distribution mirrors real-world scenarios where test suites can have:
- Tests that accidentally encode bugs as correct behavior
- Tests that pass due to specific test data
- Correct tests that expose real issues
