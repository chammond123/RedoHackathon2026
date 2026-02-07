# Buggy Inventory Management System

A deliberately buggy inventory management demo application for testing the BugFixer agent.

## Purpose

This application demonstrates how software can pass test suites while still containing bugs:

1. **Tests encoding buggy behavior** - Some tests assert the buggy behavior as correct
2. **Lucky test cases** - Tests pass due to specific edge cases or math
3. **Missing edge case coverage** - Critical scenarios not tested
4. **Global state pollution** - Test isolation issues

## Structure

```
InventoryDemo/
├── BUG_MAP.md              # Catalog of all seeded bugs
├── GENERATION_PROMPT.md    # Prompt for generating similar buggy apps
├── README.md               # This file
└── buggy_inventory/
    ├── __init__.py
    ├── __main__.py
    ├── app.py              # CLI entry point
    ├── constants.py        # Configuration constants
    ├── inventory.py        # Inventory manager with bugs
    ├── models.py           # Data models with bugs
    ├── orders.py           # Order processing with bugs
    ├── pricing.py          # Pricing calculations with bugs
    ├── storage.py          # Persistence layer with bugs
    └── tests/
        ├── test_inventory.py
        ├── test_models.py
        ├── test_orders.py
        ├── test_pricing.py
        └── test_storage.py
```

## Bug Categories

| Category | Count | Examples |
|----------|-------|----------|
| Logic | 12 | Off-by-one, wrong operators, inverted conditions |
| Validation | 8 | Missing checks, silent acceptance |
| State | 5 | Mutable defaults, missing updates |
| Precision | 6 | Rounding, floating point |
| Coupling | 3 | Global state, test pollution |
| Error Handling | 4 | Silent failures |

## Running Tests

```bash
cd InventoryDemo
pytest buggy_inventory/tests/ -v
```

Expected results:
- ~75 tests pass (including those encoding buggy behavior)
- ~5 tests fail (exposing actual bugs)

## Example Bugs

### Bug #10: total_items() Returns Line Count
```python
def total_items(self) -> int:
    # BUG: Returns count of lines, not sum of quantities
    return len(self.lines)
```

### Bug #45: Margin vs Markup
```python
def calculate_margin(cost: float, price: float) -> float:
    # BUG: Calculates markup, not margin
    return ((price - cost) / cost) * 100  # Should be / price
```

### Bug #49: Silent Save Failure
```python
def save(self, data: Dict) -> bool:
    try:
        # ... save logic ...
    except Exception:
        # BUG: Swallows exception, returns True anyway
        return True
```

## Using with BugFixer

```bash
bugfixer run --repo ./InventoryDemo/
```

The agent will:
1. Analyze the codebase
2. Run tests to identify failures
3. Form hypotheses about root causes
4. Generate patches
5. Validate fixes

## Files for Reference

- [BUG_MAP.md](BUG_MAP.md) - Complete bug catalog with line numbers
- [GENERATION_PROMPT.md](GENERATION_PROMPT.md) - Prompt for generating similar apps
