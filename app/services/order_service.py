"""Confirmación de pedidos y consultas de los pedidos del usuario."""

import hmac
import secrets
from typing import Any

from flask import session as flask_session

CHECKOUT_REJECTED_MESSAGE = "La confirmación no es válida o ya se usó."


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
