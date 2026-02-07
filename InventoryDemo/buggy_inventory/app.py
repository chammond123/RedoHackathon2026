"""CLI entry point for the inventory management system."""

import argparse
import sys
from typing import Optional

from .inventory import InventoryManager, get_manager, reset_manager
from .orders import OrderProcessor, get_processor
from .pricing import calculate_bulk_discount, format_currency
from .storage import InventoryStorage, OrderStorage


def main(args: Optional[list] = None):
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Buggy Inventory Management System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add product command
    add_parser = subparsers.add_parser("add", help="Add a product")
    add_parser.add_argument("sku", help="Product SKU")
    add_parser.add_argument("name", help="Product name")
    add_parser.add_argument("price", type=float, help="Unit price")
    add_parser.add_argument("--stock", type=int, default=0, help="Initial stock")
    add_parser.add_argument("--category", default="general", help="Product category")
    
    # List products command
    list_parser = subparsers.add_parser("list", help="List products")
    list_parser.add_argument("--low-stock", action="store_true", help="Show low stock only")
    
    # Update stock command
    stock_parser = subparsers.add_parser("stock", help="Update stock")
    stock_parser.add_argument("sku", help="Product SKU")
    stock_parser.add_argument("change", type=int, help="Stock change (+/-)")
    
    # Order command
    order_parser = subparsers.add_parser("order", help="Create an order")
    order_parser.add_argument("--customer", required=True, help="Customer ID")
    order_parser.add_argument("--items", required=True, help="Items as SKU:QTY,SKU:QTY")
    
    # Reorder check command
    subparsers.add_parser("reorder", help="Check items needing reorder")
    
    # Summary command
    subparsers.add_parser("summary", help="Show inventory summary")
    
    parsed = parser.parse_args(args)
    manager = get_manager()
    
    if parsed.command == "add":
        product = manager.add_product(
            sku=parsed.sku,
            name=parsed.name,
            price=parsed.price,
            category=parsed.category,
            initial_stock=parsed.stock,
        )
        print(f"Added product: {product.sku} - {product.name} @ {format_currency(product.price)}")
    
    elif parsed.command == "list":
        if parsed.low_stock:
            items = manager.get_low_stock_items()
            print(f"Low stock items ({len(items)}):")
            for item in items:
                print(f"  {item.product.sku}: {item.quantity} units")
        else:
            summary = manager.get_inventory_summary()
            print(f"Total products: {summary['total_products']}")
            print(f"Total units: {summary['total_units']}")
            print(f"Total value: {summary['total_value_display']}")
    
    elif parsed.command == "stock":
        success, new_qty = manager.update_stock(parsed.sku, parsed.change)
        if success:
            print(f"Updated {parsed.sku}: new quantity = {new_qty}")
        else:
            print(f"Failed to update stock for {parsed.sku}")
            sys.exit(1)
    
    elif parsed.command == "order":
        # Parse items
        items = []
        for item_str in parsed.items.split(","):
            sku, qty = item_str.split(":")
            items.append({"sku": sku.strip(), "quantity": int(qty)})
        
        processor = get_processor()
        order, warnings = processor.create_order(parsed.customer, items)
        
        print(f"Created order: {order.order_id}")
        for warning in warnings:
            print(f"  Warning: {warning}")
        
        total_info = processor.calculate_order_total(order.order_id)
        print(f"  Subtotal: {format_currency(total_info['subtotal'])}")
        print(f"  Tax: {format_currency(total_info['tax'])}")
        print(f"  Total: {format_currency(total_info['total'])}")
    
    elif parsed.command == "reorder":
        reorder_list = manager.check_reorder_needed()
        if not reorder_list:
            print("No items need reordering")
        else:
            print(f"Items needing reorder ({len(reorder_list)}):")
            for item in reorder_list:
                print(f"  [{item['priority'].upper()}] {item['sku']}: "
                      f"{item['current_stock']} units (reorder point: {item['reorder_point']})")
    
    elif parsed.command == "summary":
        summary = manager.get_inventory_summary()
        print("=== Inventory Summary ===")
        print(f"Products: {summary['total_products']}")
        print(f"Inventory items: {summary['total_inventory_items']}")
        print(f"Total units: {summary['total_units']}")
        print(f"Total value: {summary['total_value_display']}")
        print(f"Low stock items: {summary['low_stock_count']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
