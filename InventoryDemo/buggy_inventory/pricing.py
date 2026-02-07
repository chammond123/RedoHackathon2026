"""Pricing and discount calculation utilities."""

from typing import List, Dict, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP

from .constants import (
    BULK_DISCOUNT_THRESHOLD,
    BULK_DISCOUNT_RATE,
    WHOLESALE_THRESHOLD,
    WHOLESALE_DISCOUNT_RATE,
    DEFAULT_TAX_RATE,
)


def calculate_bulk_discount(quantity: int, unit_price: float) -> Tuple[float, float]:
    """
    Calculate bulk discount based on quantity.
    Returns (discounted_total, discount_amount).
    """
    base_total = quantity * unit_price
    
    # BUG #34: Uses >= for threshold but discount tiers overlap
    # Quantity of 500 qualifies for BOTH bulk and wholesale
    if quantity >= WHOLESALE_THRESHOLD:
        discount = base_total * WHOLESALE_DISCOUNT_RATE
    elif quantity >= BULK_DISCOUNT_THRESHOLD:
        discount = base_total * BULK_DISCOUNT_RATE
    else:
        discount = 0.0
    
    # BUG #35: Returns raw float without rounding
    # Can return values like 89.99999999999999
    return (base_total - discount, discount)


def calculate_tiered_discount(quantity: int, unit_price: float) -> float:
    """
    Calculate tiered discount where different quantities get different rates.
    - First 10: no discount
    - 11-50: 5% discount
    - 51-100: 10% discount  
    - 100+: 15% discount
    """
    total = 0.0
    remaining = quantity
    
    # First 10 at full price
    tier1 = min(remaining, 10)
    total += tier1 * unit_price
    remaining -= tier1
    
    # Next 40 (11-50) at 5% off
    tier2 = min(remaining, 40)
    total += tier2 * unit_price * 0.95
    remaining -= tier2
    
    # Next 50 (51-100) at 10% off
    tier3 = min(remaining, 50)
    total += tier3 * unit_price * 0.90
    remaining -= tier3
    
    # BUG #36: Rest at 15% off, but boundary is wrong
    # 101+ should get 15%, but quantity of exactly 100 falls through incorrectly
    if remaining > 0:
        total += remaining * unit_price * 0.85
    
    return total


def apply_promo_code(subtotal: float, promo_code: str) -> Tuple[float, str]:
    """
    Apply a promotional code to subtotal.
    Returns (new_total, message).
    """
    # BUG #37: Promo codes are case-sensitive
    # "SAVE10" works but "save10" doesn't
    promo_codes = {
        "SAVE10": 0.10,
        "SAVE20": 0.20,
        "HALF": 0.50,
        "FREE": 1.00,  # BUG #38: Allows 100% discount - probably shouldn't exist
    }
    
    if promo_code in promo_codes:
        discount_rate = promo_codes[promo_code]
        discount = subtotal * discount_rate
        return (subtotal - discount, f"Applied {promo_code}: -{discount:.2f}")
    
    return (subtotal, "Invalid promo code")


def calculate_shipping(subtotal: float, weight_kg: float, express: bool = False) -> float:
    """Calculate shipping cost."""
    # Base shipping
    if subtotal >= 100:
        base_shipping = 0.0  # Free shipping over $100
    else:
        base_shipping = 5.99
    
    # Weight surcharge
    # BUG #39: Uses integer division, loses precision
    weight_surcharge = int(weight_kg) * 0.50
    
    # Express multiplier
    if express:
        # BUG #40: Adds 50% to base only, not to weight surcharge
        return (base_shipping * 1.5) + weight_surcharge
    
    return base_shipping + weight_surcharge


def calculate_tax(amount: float, tax_rate: float = DEFAULT_TAX_RATE, 
                  tax_exempt: bool = False) -> float:
    """Calculate tax on an amount."""
    if tax_exempt:
        return 0.0
    
    # BUG #41: Rounds tax incorrectly - uses round() which does banker's rounding
    # round(2.675, 2) = 2.67 (not 2.68)
    return round(amount * tax_rate, 2)


def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    # BUG #42: Doesn't handle negative amounts properly
    # -5.00 becomes "$-5.00" instead of "-$5.00"
    return f"${amount:.2f}"


def parse_currency(currency_str: str) -> float:
    """Parse a currency string to float."""
    # BUG #43: Doesn't handle various currency formats
    # Assumes "$X.XX" format, fails on "X.XX", "$X", "X"
    try:
        cleaned = currency_str.replace("$", "").replace(",", "")
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0  # BUG #44: Returns 0 instead of raising error


def calculate_margin(cost: float, price: float) -> float:
    """Calculate profit margin percentage."""
    if price == 0:
        return 0.0
    
    # BUG #45: Calculates markup, not margin
    # Margin = (price - cost) / price
    # Markup = (price - cost) / cost (what this does)
    return ((price - cost) / cost) * 100


def split_payment(total: float, num_payments: int) -> List[float]:
    """Split total into equal payments."""
    if num_payments <= 0:
        return [total]
    
    # BUG #46: Simple division loses pennies
    # $100.00 / 3 = $33.33 each = $99.99 total (loses $0.01)
    payment = round(total / num_payments, 2)
    return [payment] * num_payments


def calculate_order_total_precise(items: List[Dict], tax_rate: float = DEFAULT_TAX_RATE,
                                   promo_code: Optional[str] = None) -> Dict:
    """
    Calculate complete order total using Decimal for precision.
    items: List of {"quantity": int, "unit_price": float, "discount": float}
    """
    subtotal = Decimal("0.00")
    
    for item in items:
        qty = item["quantity"]
        price = Decimal(str(item["unit_price"]))
        discount = Decimal(str(item.get("discount", 0)))
        
        # BUG #47: Applies discount per-item before summing
        # Rounding errors accumulate
        item_total = (price * qty * (1 - discount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        subtotal += item_total
    
    # Apply promo code if provided
    promo_discount = Decimal("0.00")
    if promo_code:
        # BUG #48: Uses float promo calculation, converting back to Decimal
        # Loses the precision benefit
        promo_total, _ = apply_promo_code(float(subtotal), promo_code)
        promo_discount = subtotal - Decimal(str(promo_total))
        subtotal = Decimal(str(promo_total))
    
    tax = (subtotal * Decimal(str(tax_rate))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = subtotal + tax
    
    return {
        "subtotal": float(subtotal),
        "promo_discount": float(promo_discount),
        "tax": float(tax),
        "total": float(total),
    }
