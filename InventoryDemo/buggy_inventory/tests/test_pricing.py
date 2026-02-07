"""Tests for pricing and discount calculations."""

import pytest
from decimal import Decimal

from buggy_inventory.pricing import (
    calculate_bulk_discount,
    calculate_tiered_discount,
    apply_promo_code,
    calculate_shipping,
    calculate_tax,
    format_currency,
    parse_currency,
    calculate_margin,
    split_payment,
    calculate_order_total_precise,
)


class TestBulkDiscount:
    """Tests for bulk discount calculations."""
    
    def test_no_discount_below_threshold(self):
        """Test no discount for small quantities."""
        total, discount = calculate_bulk_discount(50, 10.00)
        assert discount == 0.0
        assert total == 500.00
    
    def test_bulk_discount_at_threshold(self):
        """Test 10% discount at bulk threshold (100)."""
        total, discount = calculate_bulk_discount(100, 10.00)
        # 100 * 10 = 1000, 10% off = 900
        assert discount == 100.00
        assert total == 900.00
    
    def test_wholesale_discount_at_threshold(self):
        """Test 15% discount at wholesale threshold (500)."""
        total, discount = calculate_bulk_discount(500, 10.00)
        # 500 * 10 = 5000, 15% off = 4250
        assert discount == 750.00
        assert total == 4250.00
    
    def test_bulk_discount_precision_issue(self):
        """Test that bulk discount has precision issues."""
        # This test PASSES due to lucky math - Bug #35 doesn't show here
        total, discount = calculate_bulk_discount(100, 9.99)
        # 100 * 9.99 = 999, 10% = 99.9
        # Lucky: these values don't cause visible float issues
        assert total == pytest.approx(899.1)
        assert discount == pytest.approx(99.9)


class TestTieredDiscount:
    """Tests for tiered discount calculations."""
    
    def test_tier1_no_discount(self):
        """Test first 10 units at full price."""
        total = calculate_tiered_discount(10, 10.00)
        assert total == 100.00
    
    def test_tier2_five_percent(self):
        """Test 11-50 units at 5% off."""
        total = calculate_tiered_discount(50, 10.00)
        # First 10: 10 * 10 = 100
        # Next 40: 40 * 10 * 0.95 = 380
        # Total: 480
        assert total == 480.00
    
    def test_tier3_ten_percent(self):
        """Test 51-100 units at 10% off."""
        total = calculate_tiered_discount(100, 10.00)
        # First 10: 100
        # Next 40: 380
        # Next 50: 50 * 10 * 0.90 = 450
        # Total: 930
        assert total == 930.00
    
    def test_tier4_boundary_bug(self):
        """Test tier 4 boundary condition."""
        # This test FAILS - exposes Bug #36
        # Quantity of exactly 100 should NOT get 15% tier
        total_100 = calculate_tiered_discount(100, 10.00)
        total_101 = calculate_tiered_discount(101, 10.00)
        
        # 101 units should have 1 unit at 15% off: 10 * 0.85 = 8.50
        # So total_101 = 930 + 8.50 = 938.50
        expected_101 = 930.00 + 8.50
        assert total_101 == pytest.approx(expected_101)
        
        # 100 units should be exactly 930
        assert total_100 == 930.00  # PASSES - boundary is actually correct


class TestPromoCode:
    """Tests for promo code application."""
    
    def test_valid_promo_code(self):
        """Test applying valid promo code."""
        total, message = apply_promo_code(100.00, "SAVE10")
        assert total == 90.00
        assert "Applied" in message
    
    def test_invalid_promo_code(self):
        """Test invalid promo code."""
        total, message = apply_promo_code(100.00, "INVALID")
        assert total == 100.00
        assert "Invalid" in message
    
    def test_promo_code_case_sensitive(self):
        """Test that promo codes are case-sensitive."""
        # This test PASSES - encodes Bug #37 behavior
        total_upper, _ = apply_promo_code(100.00, "SAVE10")
        total_lower, _ = apply_promo_code(100.00, "save10")
        
        assert total_upper == 90.00  # Valid
        assert total_lower == 100.00  # BUG: case mismatch rejected
    
    def test_free_promo_code_exists(self):
        """Test that FREE promo code gives 100% discount."""
        # This test PASSES - encodes Bug #38 behavior
        total, _ = apply_promo_code(100.00, "FREE")
        assert total == 0.00  # BUG: probably shouldn't allow 100% off


class TestShipping:
    """Tests for shipping calculations."""
    
    def test_free_shipping_over_100(self):
        """Test free shipping for orders over $100."""
        cost = calculate_shipping(150.00, 5.0)
        # Base: 0, weight: 5 * 0.50 = 2.50
        assert cost == 2.50
    
    def test_base_shipping_under_100(self):
        """Test base shipping for orders under $100."""
        cost = calculate_shipping(50.00, 0.0)
        assert cost == 5.99
    
    def test_weight_surcharge_integer_division(self):
        """Test weight surcharge uses integer division."""
        # This test PASSES - encodes Bug #39 behavior
        cost = calculate_shipping(150.00, 5.9)
        # BUG: int(5.9) = 5, not 6
        # Weight surcharge: 5 * 0.50 = 2.50
        assert cost == 2.50
    
    def test_express_shipping_base_only(self):
        """Test express adds 50% to base only."""
        # This test PASSES - encodes Bug #40 behavior
        cost = calculate_shipping(50.00, 10.0, express=True)
        # Base: 5.99 * 1.5 = 8.985
        # Weight: 10 * 0.50 = 5.00
        # BUG: express doesn't apply to weight surcharge
        # Total: 8.985 + 5.00 = 13.985
        assert cost == pytest.approx(13.985)


class TestTax:
    """Tests for tax calculations."""
    
    def test_basic_tax(self):
        """Test basic tax calculation."""
        tax = calculate_tax(100.00)
        assert tax == 8.00
    
    def test_tax_exempt(self):
        """Test tax exempt calculation."""
        tax = calculate_tax(100.00, tax_exempt=True)
        assert tax == 0.00
    
    def test_tax_rounding_bankers(self):
        """Test that tax uses banker's rounding."""
        # This test demonstrates Bug #41 - Python's round() behavior
        # Due to float representation, 33.4375 * 0.08 = 2.675000000000001
        # which rounds to 2.68, not 2.67
        tax = calculate_tax(33.4375, 0.08)
        # Float precision causes this to round up
        assert tax == 2.68


class TestCurrencyFormatting:
    """Tests for currency formatting."""
    
    def test_format_positive(self):
        """Test formatting positive amount."""
        result = format_currency(19.99)
        assert result == "$19.99"
    
    def test_format_negative_wrong_position(self):
        """Test negative amount formatting."""
        # This test PASSES - encodes Bug #42 behavior
        result = format_currency(-5.00)
        assert result == "$-5.00"  # BUG: should be "-$5.00"
    
    def test_parse_currency_standard(self):
        """Test parsing standard currency format."""
        result = parse_currency("$19.99")
        assert result == 19.99
    
    def test_parse_currency_no_dollar_sign(self):
        """Test parsing without dollar sign."""
        result = parse_currency("19.99")
        assert result == 19.99
    
    def test_parse_currency_invalid_returns_zero(self):
        """Test that invalid currency returns 0."""
        # This test PASSES - encodes Bug #44 behavior
        result = parse_currency("not a number")
        assert result == 0.0  # BUG: should raise error


class TestMargin:
    """Tests for margin calculations."""
    
    def test_margin_calculation(self):
        """Test margin calculation."""
        # This test FAILS - exposes Bug #45
        # Margin = (price - cost) / price * 100
        # Markup = (price - cost) / cost * 100
        margin = calculate_margin(60.00, 100.00)
        # Expected margin: (100 - 60) / 100 * 100 = 40%
        # Bug returns markup: (100 - 60) / 60 * 100 = 66.67%
        assert margin == pytest.approx(40.0)  # FAILS: returns 66.67
    
    def test_markup_calculation_encoded(self):
        """Test that calculate_margin actually returns markup."""
        # This test PASSES - encodes Bug #45 behavior
        markup = calculate_margin(60.00, 100.00)
        expected_markup = ((100 - 60) / 60) * 100  # 66.67%
        assert markup == pytest.approx(expected_markup)


class TestSplitPayment:
    """Tests for payment splitting."""
    
    def test_even_split(self):
        """Test even payment split."""
        payments = split_payment(100.00, 4)
        assert payments == [25.00, 25.00, 25.00, 25.00]
        assert sum(payments) == 100.00
    
    def test_split_loses_pennies(self):
        """Test that split can lose pennies."""
        # This test PASSES - encodes Bug #46 behavior
        payments = split_payment(100.00, 3)
        # 100 / 3 = 33.333... rounds to 33.33
        assert payments == [33.33, 33.33, 33.33]
        # BUG: sum is 99.99, loses $0.01
        assert sum(payments) == 99.99
    
    def test_split_preserves_total(self):
        """Test that split preserves total."""
        # This test FAILS - exposes Bug #46
        payments = split_payment(100.00, 3)
        assert sum(payments) == 100.00  # FAILS: sum is 99.99


class TestPreciseOrderTotal:
    """Tests for precise order total calculation."""
    
    def test_basic_order_total(self):
        """Test basic order total calculation."""
        items = [
            {"quantity": 2, "unit_price": 10.00},
            {"quantity": 3, "unit_price": 20.00},
        ]
        result = calculate_order_total_precise(items)
        
        assert result["subtotal"] == 80.00  # 20 + 60
        assert result["tax"] == 6.40  # 80 * 0.08
        assert result["total"] == 86.40
    
    def test_order_total_with_promo(self):
        """Test order total with promo code."""
        items = [{"quantity": 10, "unit_price": 10.00}]
        result = calculate_order_total_precise(items, promo_code="SAVE10")
        
        assert result["subtotal"] == 90.00  # 100 - 10%
        assert result["promo_discount"] == 10.00
    
    def test_order_total_precision_loss(self):
        """Test that promo calculation loses precision."""
        # This test demonstrates Bug #48
        # The function converts to float for promo, losing Decimal precision
        items = [{"quantity": 3, "unit_price": 33.33}]
        result = calculate_order_total_precise(items, promo_code="SAVE10")
        
        # With pure Decimal: 99.99 - 10% = 89.991 -> 89.99
        # With float conversion: may have slight variations
        assert result["subtotal"] == pytest.approx(89.99, abs=0.01)
