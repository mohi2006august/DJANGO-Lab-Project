"""
Demo repository generator for CodeDNA.
Produces a rich, realistic sample e-commerce Python application ZIP
demonstrating multi-tier architecture, circular dependency detection, and hotspots.
"""
import io
import zipfile

SAMPLE_FILES = {
    "manage.py": '''"""
Django-style management script for the demo shop project.
"""
import sys

def main():
    print("CodeDNA Demo Shop runner")

if __name__ == "__main__":
    main()
''',

    "shop/__init__.py": '''"""Shop application package."""
__version__ = "1.0.0"
''',

    "shop/models.py": '''"""
Database domain models for products, users, and orders.
"""

class Product:
    """Represents an item in the catalog."""
    def __init__(self, product_id: int, name: str, price: float, stock: int = 0):
        self.id = product_id
        self.name = name
        self.price = price
        self.stock = stock

    def is_in_stock(self) -> bool:
        """Check if inventory is available."""
        return self.stock > 0

    def adjust_inventory(self, delta: int):
        """Update stock quantity safely."""
        if self.stock + delta < 0:
            raise ValueError("Insufficient inventory")
        self.stock += delta


class Customer:
    """Represents a registered shopper."""
    def __init__(self, user_id: int, username: str, email: str):
        self.id = user_id
        self.username = username
        self.email = email
        self.is_active = True


class Order:
    """Represents a customer purchase order."""
    def __init__(self, order_id: str, customer: Customer, total_amount: float):
        self.id = order_id
        self.customer = customer
        self.total_amount = total_amount
        self.status = "pending"
        self.items = []

    def mark_paid(self):
        """Transition order status to paid."""
        self.status = "paid"
''',

    "shop/utils.py": '''"""
Reusable helper utilities for text processing, formatting, and cryptography.
"""
import re
import hashlib

def slugify(text: str) -> str:
    """Convert text into URL-friendly slug."""
    text = text.lower().strip()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def format_currency(amount: float, symbol: str = "$") -> str:
    """Format floating point price into currency string."""
    return f"{symbol}{amount:,.2f}"

def hash_token(token: str) -> str:
    """Generate SHA-256 fingerprint for auth tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
''',

    "shop/auth.py": '''"""
Authentication and security services for user sessions.
"""
from shop.models import Customer
from shop.utils import hash_token

class AuthService:
    """Handles token authentication and customer validation."""
    def __init__(self):
        self.active_sessions = {}

    def authenticate(self, username: str, password_hash: str) -> bool:
        """Validate credentials against customer record."""
        return len(username) > 3 and len(password_hash) == 64

    def create_session(self, customer: Customer) -> str:
        """Generate token and register customer session."""
        token = hash_token(f"{customer.id}:{customer.email}")
        self.active_sessions[token] = customer.id
        return token
''',

    "shop/cart.py": '''"""
Shopping cart state management and calculations.
"""
from shop.models import Product
from shop.utils import format_currency

class CartItem:
    """Line item in a shopping cart."""
    def __init__(self, product: Product, quantity: int = 1):
        self.product = product
        self.quantity = quantity

    def subtotal(self) -> float:
        """Compute line item price."""
        return self.product.price * self.quantity


class Cart:
    """Aggregates items and computes cart totals."""
    def __init__(self):
        self.items = []

    def add_product(self, product: Product, quantity: int = 1):
        """Add item to cart or increment quantity."""
        for item in self.items:
            if item.product.id == product.id:
                item.quantity += quantity
                return
        self.items.append(CartItem(product, quantity))

    def total(self) -> float:
        """Sum of all cart item subtotals."""
        return sum(item.subtotal() for item in self.items)

    def formatted_total(self) -> str:
        """Human-readable cart total."""
        return format_currency(self.total())
''',

    "shop/services.py": '''"""
Business logic coordinator for orders, inventory, and payments.
"""
from shop.models import Product, Order, Customer
from shop.cart import Cart
from shop.utils import format_currency
from shop.notifications import NotificationService

class OrderService:
    """Coordinates checkout flow, inventory deduction, and billing."""
    def __init__(self):
        self.notifier = NotificationService()

    def checkout(self, customer: Customer, cart: Cart) -> Order:
        """Execute checkout process for cart contents."""
        if not cart.items:
            raise ValueError("Cannot checkout empty cart")

        for item in cart.items:
            item.product.adjust_inventory(-item.quantity)

        order = Order(order_id="ORD-9901", customer=customer, total_amount=cart.total())
        order.mark_paid()
        self.notifier.send_order_confirmation(customer, order)
        return order

    def calculate_tax(self, amount: float, tax_rate: float = 0.08) -> float:
        """Compute sales tax for amount."""
        return round(amount * tax_rate, 2)
''',

    "shop/notifications.py": '''"""
Customer communication and dispatch service.
"""
from shop.models import Customer, Order
from shop.utils import format_currency

class NotificationService:
    """Sends transactional receipts and system alerts."""
    def __init__(self, email_backend: str = "smtp"):
        self.backend = email_backend

    def send_order_confirmation(self, customer: Customer, order: Order):
        """Send purchase confirmation receipt to shopper."""
        formatted_price = format_currency(order.total_amount)
        print(f"Dispatched email to {customer.email} for order {order.id}: {formatted_price}")

    def notify_admin_low_stock(self, product_name: str, stock_level: int):
        """Alert store admin when item inventory drops."""
        print(f"ALERT: Product {product_name} low stock: {stock_level}")
''',

    "shop/views.py": '''"""
Controller views for web presentation layer.
"""
from shop.models import Product, Customer
from shop.services import OrderService
from shop.cart import Cart
from shop.auth import AuthService
from shop.utils import format_currency

def product_list_view():
    """Render catalog listing."""
    p1 = Product(1, "Mechanical Keyboard", 149.99, 12)
    p2 = Product(2, "Ergonomic Mouse", 79.99, 8)
    return [p1, p2]

def checkout_view(customer_id: int):
    """Handle order processing view."""
    auth = AuthService()
    customer = Customer(customer_id, "coder", "dev@example.com")
    cart = Cart()
    cart.add_product(Product(1, "Mechanical Keyboard", 149.99, 12), 1)

    order_svc = OrderService()
    order = order_svc.checkout(customer, cart)
    return {"status": "success", "order_id": order.id, "total": format_currency(order.total_amount)}
''',

    "shop/api.py": '''"""
REST API endpoints for mobile and headless consumers.
"""
from shop.models import Product
from shop.services import OrderService
from shop.auth import AuthService
from shop.cart import Cart

def api_health():
    """Health check probe endpoint."""
    return {"status": "ok", "service": "shop-api"}

def api_catalog():
    """Retrieve catalog payload."""
    return [{"id": 1, "name": "Mechanical Keyboard", "price": 149.99}]

def api_place_order(auth_token: str, items: list):
    """Authenticated endpoint to submit purchase order."""
    auth = AuthService()
    if not auth.authenticate("dev", auth_token):
        return {"error": "Unauthorized"}, 401
    return {"status": "created", "order_id": "ORD-API-101"}
''',
}

def generate_sample_zip_bytes() -> bytes:
    """Generate in-memory ZIP bytes containing the demo repository."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in SAMPLE_FILES.items():
            zf.writestr(filename, content)
    buf.seek(0)
    return buf.getvalue()

