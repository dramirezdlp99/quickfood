"""Confirmación de pedidos y consultas de los pedidos del usuario."""

import hmac
import secrets
from typing import Any

from flask import session as flask_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Order, OrderItem, Product
from .cart_service import MAX_DB_ID, CartService

CHECKOUT_REJECTED_MESSAGE = "La confirmación no es válida o ya se usó."


class EmptyCartError(ValueError):
    """No se puede confirmar un carrito sin productos."""


class PriceChangedError(ValueError):
    """El total cambió desde que el usuario vio el resumen."""


class InvalidCheckoutTokenError(ValueError):
    """El token de confirmación no existe, ya se usó o no coincide."""


class CheckoutToken:
    """Token de confirmación de un solo uso guardado en la sesión (evita el doble envío)."""

    KEY = "checkout"

    def __init__(self, storage: Any | None = None) -> None:
        self._session = storage if storage is not None else flask_session

    def issue(self, total: int) -> str:
        """Genera un token nuevo y recuerda el total que vio el usuario."""
        token = secrets.token_urlsafe(32)
        self._session[self.KEY] = {"token": token, "total": total}
        return token

    def consume(self, submitted: Any) -> int:
        """Devuelve el total esperado; el token se descarta siempre, sea válido o no."""
        stored = self._session.pop(self.KEY, None)
        if not isinstance(stored, dict) or not isinstance(submitted, str):
            raise InvalidCheckoutTokenError(CHECKOUT_REJECTED_MESSAGE)
        token, total = stored.get("token"), stored.get("total")
        if not isinstance(token, str) or not isinstance(total, int):
            raise InvalidCheckoutTokenError(CHECKOUT_REJECTED_MESSAGE)
        if not hmac.compare_digest(token.encode(), submitted.encode()):
            raise InvalidCheckoutTokenError(CHECKOUT_REJECTED_MESSAGE)
        return total


class OrderPlacer:
    """Crea el pedido desde el carrito en una sola transacción."""

    def __init__(self, cart: CartService) -> None:
        self.cart = cart

    def place(self, user_id: int, expected_total: int) -> Order:
        """Guarda el pedido con precios de la BD y vacía el carrito solo si se guardó."""
        summary = self.cart.summary()
        if not summary.lines:
            raise EmptyCartError("Tu carrito está vacío.")
        if summary.total != expected_total:
            raise PriceChangedError("Los precios cambiaron; revisa el nuevo total.")

        order = Order(
            user_id=user_id,
            total=summary.total,
            items=[
                OrderItem(product=line.product, quantity=line.quantity, unit_price=line.product.price)
                for line in summary.lines
            ],
        )
        db.session.add(order)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
        self.cart.clear()
        return order


class OrderQueries:
    """Consulta pedidos siempre filtrando por su dueño."""

    @staticmethod
    def list_for_user(user_id: int) -> list[Order]:
        """Pedidos del usuario, del más reciente al más antiguo."""
        return (
            Order.query.options(selectinload(Order.items))
            .filter_by(user_id=user_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .all()
        )

    @staticmethod
    def get_for_user(order_id: int, user_id: int) -> Order | None:
        """El pedido solo si pertenece al usuario; si no, None (la ruta responde 404)."""
        if not 1 <= order_id <= MAX_DB_ID:
            return None  # un id gigante causaría OverflowError (500) en la BD
        return (
            Order.query.options(selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.restaurant))
            .filter_by(id=order_id, user_id=user_id)
            .first()
        )
