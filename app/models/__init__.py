"""Modelos de datos (contrato compartido por el equipo).

Si un módulo necesita un campo nuevo, se agrega en su archivo y se avisa
en el Pull Request para que los demás lo tengan en cuenta.
"""

from .user import User
from .restaurant import Restaurant
from .product import Product
from .order import Order, OrderItem

__all__ = ["User", "Restaurant", "Product", "Order", "OrderItem"]
