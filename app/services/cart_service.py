"""Servicios y estructuras para gestionar el carrito de compras."""

from dataclasses import dataclass
from typing import Any

from flask import session as flask_session

from ..extensions import db
from ..models import Product

MAX_QUANTITY = 20
MAX_PRODUCT_ID = 2**31 - 1  # límite de INTEGER en SQLite/PostgreSQL
QUANTITY_ERROR = f"La cantidad debe ser un número entero entre 1 y {MAX_QUANTITY}."
INVALID_PRODUCT_ERROR = "El producto seleccionado no es válido."


class InvalidQuantityError(ValueError):
    """La cantidad no es un entero entre 1 y el máximo permitido."""


class InvalidProductIdError(ValueError):
    """El identificador del producto no es válido."""


class QuantityValidator:
    """Convierte y valida cantidades de productos."""

    @staticmethod
    def validate(value: Any) -> int:
        """Devuelve la cantidad como entero si está entre 1 y el máximo."""
        if isinstance(value, str) and value.strip().isdecimal():
            value = int(value)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_QUANTITY:
            raise InvalidQuantityError(QUANTITY_ERROR)
        return value


class CartStorage:
    """Lee y escribe el carrito en una sesión compatible con Flask."""

    def __init__(self, storage: Any | None = None) -> None:
        self._session = storage if storage is not None else flask_session

    def read(self) -> dict[int, int]:
        """Normaliza las claves de sesión a enteros en un solo lugar."""
        raw_cart = self._session.get("cart", {})
        if not isinstance(raw_cart, dict):
            self.write({})
            return {}

        normalized: dict[int, int] = {}
        for raw_id, raw_quantity in raw_cart.items():
            try:
                product_id = int(raw_id)
                quantity = int(raw_quantity)
            except (TypeError, ValueError):
                continue
            if product_id > 0 and quantity > 0:
                normalized[product_id] = quantity

        self.write(normalized)
        return normalized

    def write(self, cart: dict[int, int]) -> None:
        """Guarda únicamente identificadores y cantidades en la sesión."""
        self._session["cart"] = {str(product_id): quantity for product_id, quantity in cart.items()}


@dataclass(frozen=True)
class CartLine:
    """Una línea del carrito con su subtotal calculado."""

    product: Product
    quantity: int
    subtotal: int


@dataclass(frozen=True)
class CartSummary:
    """Líneas y total del carrito."""

    lines: tuple[CartLine, ...]
    total: int


class CartService:
    """Gestiona cantidades y construye resúmenes con precios de la base de datos."""

    def __init__(self, storage: CartStorage) -> None:
        self.storage = storage

    def add(self, product_id: Any, quantity: Any) -> None:
        """Agrega unidades de un producto existente al carrito."""
        product = self._get_product(product_id)
        amount = QuantityValidator.validate(quantity)
        cart = self.storage.read()
        cart[product.id] = QuantityValidator.validate(cart.get(product.id, 0) + amount)
        self.storage.write(cart)

    def update(self, product_id: Any, quantity: Any) -> bool:
        """Actualiza una línea; cero elimina la línea del carrito."""
        product_id = self._normalize_product_id(product_id)
        self._get_product(product_id)
        cart = self.storage.read()
        if product_id not in cart:
            return False
        if quantity == 0 or quantity == "0":
            cart.pop(product_id)
            self.storage.write(cart)
            return True

        cart[product_id] = QuantityValidator.validate(quantity)
        self.storage.write(cart)
        return True

    def remove(self, product_id: Any) -> bool:
        """Elimina un producto del carrito si está presente."""
        product = self._get_product(product_id)
        cart = self.storage.read()
        if product.id not in cart:
            return False
        cart.pop(product.id)
        self.storage.write(cart)
        return True

    def summary(self) -> CartSummary:
        """Calcula subtotales y total usando productos persistidos."""
        cart = self.storage.read()
        products = Product.query.filter(Product.id.in_(cart)).all() if cart else []
        product_by_id = {product.id: product for product in products}
        valid_cart = {product_id: quantity for product_id, quantity in cart.items() if product_id in product_by_id}
        self.storage.write(valid_cart)

        lines = tuple(
            CartLine(
                product=product_by_id[product_id],
                quantity=quantity,
                subtotal=product_by_id[product_id].price * quantity,
            )
            for product_id, quantity in valid_cart.items()
        )
        return CartSummary(lines=lines, total=sum(line.subtotal for line in lines))

    @staticmethod
    def _normalize_product_id(value: Any) -> int:
        """Convierte el identificador recibido o lanza un error de dominio."""
        try:
            product_id = int(value)
        except (TypeError, ValueError) as error:
            raise InvalidProductIdError(INVALID_PRODUCT_ERROR) from error
        if not 1 <= product_id <= MAX_PRODUCT_ID:
            raise InvalidProductIdError(INVALID_PRODUCT_ERROR)
        return product_id

    @classmethod
    def _get_product(cls, product_id: Any) -> Product:
        """Obtiene el producto desde la base de datos."""
        normalized_id = cls._normalize_product_id(product_id)
        product = db.session.get(Product, normalized_id)
        if product is None:
            raise InvalidProductIdError("El producto seleccionado no existe.")
        return product
