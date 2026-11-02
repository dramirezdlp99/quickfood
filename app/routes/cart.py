"""Rutas del carrito de compras."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..services.cart_service import (
    MAX_QUANTITY,
    CartService,
    CartStorage,
    InvalidProductIdError,
    InvalidQuantityError,
)

bp = Blueprint("cart", __name__, url_prefix="/carrito")

NOT_IN_CART = "El producto no está en el carrito."


def _service() -> CartService:
    """Construye el servicio para la sesión de la solicitud actual."""
    return CartService(CartStorage())


def _back_to_cart():
    """Redirige a la vista del carrito."""
    return redirect(url_for("cart.view"))


@bp.get("")
def view():
    """Muestra el contenido actual del carrito."""
    summary = _service().summary()
    return render_template("cart/view.html", summary=summary, max_quantity=MAX_QUANTITY)


@bp.post("/agregar")
def add():
    """Agrega un producto y redirige a la vista del carrito."""
    try:
        _service().add(request.form.get("product_id"), request.form.get("quantity"))
    except InvalidQuantityError as error:
        flash(str(error), "warning")
    except InvalidProductIdError:
        flash("No se pudo agregar el producto seleccionado.", "warning")
    else:
        flash("Producto agregado al carrito.", "success")
    return _back_to_cart()


@bp.post("/actualizar")
def update():
    """Actualiza la cantidad de una línea y redirige al carrito."""
    try:
        updated = _service().update(request.form.get("product_id"), request.form.get("quantity"))
    except InvalidQuantityError as error:
        flash(str(error), "warning")
    except InvalidProductIdError:
        flash("No se pudo actualizar el producto seleccionado.", "warning")
    else:
        flash("Carrito actualizado." if updated else NOT_IN_CART, "success" if updated else "warning")
    return _back_to_cart()


@bp.post("/eliminar")
def remove():
    """Elimina una línea y redirige al carrito."""
    try:
        removed = _service().remove(request.form.get("product_id"))
    except InvalidProductIdError:
        flash("No se pudo eliminar el producto seleccionado.", "warning")
    else:
        flash("Producto eliminado del carrito." if removed else NOT_IN_CART, "success" if removed else "warning")
    return _back_to_cart()
