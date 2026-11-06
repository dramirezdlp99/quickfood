"""Rutas de confirmación y consulta de pedidos del cliente."""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..services.auth_service import login_required
from ..services.cart_service import CartService, CartStorage
from ..services.order_service import (
    CheckoutToken,
    EmptyCartError,
    InvalidCheckoutTokenError,
    OrderPlacer,
    OrderQueries,
    PriceChangedError,
    checkout_fingerprint,
)

bp = Blueprint("orders", __name__, url_prefix="/pedidos")

EMPTY_CART_MESSAGE = "Tu carrito está vacío; agrega productos antes de confirmar."
COLOMBIA_TZ = timezone(timedelta(hours=-5), "COT")  # Colombia no tiene horario de verano


@bp.app_template_filter("colombia_time")
def format_colombia_time(value: datetime) -> str:
    """Fecha y hora de Colombia, p. ej. 06/11/2026 2:45 p. m. (la BD guarda UTC)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)  # SQLite devuelve la fecha sin zona
    local = value.astimezone(COLOMBIA_TZ)
    hour = local.hour % 12 or 12
    period = "a. m." if local.hour < 12 else "p. m."
    return f"{local:%d/%m/%Y} {hour}:{local:%M} {period}"


def _cart() -> CartService:
    """Carrito de la sesión actual."""
    return CartService(CartStorage())


@bp.get("/confirmar")
@login_required
def confirm_form():
    """Muestra el resumen y emite el token de confirmación."""
    summary = _cart().summary()
    if not summary.lines:
        flash(EMPTY_CART_MESSAGE, "warning")
        return redirect(url_for("cart.view"))
    token = CheckoutToken().issue(checkout_fingerprint(summary))
    return render_template("orders/confirm.html", summary=summary, checkout_token=token)


@bp.post("/confirmar")
@login_required
def confirm():
    """Crea el pedido si el token es válido y los precios no cambiaron."""
    try:
        expected = CheckoutToken().consume(request.form.get("checkout_token"))
        order = OrderPlacer(_cart()).place(g.user.id, expected)
    except InvalidCheckoutTokenError as error:
        # Si aún hay carrito (p. ej. se abrió el resumen en otra pestaña), vuelve al resumen.
        flash(str(error), "warning")
        has_cart = bool(_cart().storage.read())
        return redirect(url_for("orders.confirm_form" if has_cart else "orders.index"))
    except EmptyCartError:
        flash(EMPTY_CART_MESSAGE, "warning")
        return redirect(url_for("cart.view"))
    except PriceChangedError as error:
        flash(str(error), "warning")
        return redirect(url_for("orders.confirm_form"))
    flash(f"¡Listo! Tu pedido #{order.id} quedó confirmado.", "success")
    return redirect(url_for("orders.detail", order_id=order.id))


@bp.get("")
@login_required
def index():
    """Mis pedidos."""
    return render_template("orders/index.html", orders=OrderQueries.list_for_user(g.user.id))


@bp.get("/<int:order_id>")
@login_required
def detail(order_id: int):
    """Detalle de un pedido propio; el de otro usuario responde 404."""
    order = OrderQueries.get_for_user(order_id, g.user.id)
    if order is None:
        abort(404)
    return render_template("orders/detail.html", order=order)
