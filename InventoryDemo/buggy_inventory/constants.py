"""Constants for the inventory management system."""

# Stock thresholds
DEFAULT_REORDER_POINT = 10
DEFAULT_REORDER_QUANTITY = 50
MAX_STOCK_LIMIT = 1000

# Discount tiers
BULK_DISCOUNT_THRESHOLD = 100
BULK_DISCOUNT_RATE = 0.10  # 10% discount

WHOLESALE_THRESHOLD = 500
WHOLESALE_DISCOUNT_RATE = 0.15  # 15% discount

# Tax rate
DEFAULT_TAX_RATE = 0.08  # 8%

# Inventory file
DEFAULT_INVENTORY_FILE = "inventory.json"
DEFAULT_ORDERS_FILE = "orders.json"

# Status values
STATUS_PENDING = "pending"
STATUS_FULFILLED = "fulfilled"
STATUS_CANCELLED = "cancelled"
STATUS_BACKORDERED = "backordered"

# Priority levels for reorder
PRIORITY_LOW = "low"
PRIORITY_MEDIUM = "medium"
PRIORITY_HIGH = "high"
PRIORITY_CRITICAL = "critical"
