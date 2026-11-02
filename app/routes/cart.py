"""Rutas del carrito de compras."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..services.cart_service import (
    CartService,
    CartStorage,
    InvalidProductIdError,
    InvalidQuantityError,
)

bp = Blueprint("cart", __name__, url_prefix="/carrito")


def _service() -> CartService:
    """Construye el servicio para la sesión de la solicitud actual."""
    return CartService(CartStorage())


@bp.get("")
def view():
    """Muestra el contenido actual del carrito."""
    summary = _service().summary()
    return render_template("cart/view.html", summary=summary)


@bp.post("/agregar")
def add():
    """Agrega un producto y redirige a la vista del carrito."""
    try:
        _service().add(request.form.get("product_id"), request.form.get("quantity"))
    except InvalidQuantityError:
        flash("La cantidad debe ser un número entero entre 1 y 20.", "warning")
    except InvalidProductIdError:
        flash("No se pudo agregar el producto seleccionado.", "warning")
    else:
        flash("Producto agregado al carrito.", "success")
    return redirect(url_for("cart.view"))


@bp.post("/actualizar")
def update():
    """Actualiza la cantidad de una línea y redirige al carrito."""
    try:
        updated = _service().update(request.form.get("product_id"), request.form.get("quantity"))
    except InvalidQuantityError:
        flash("La cantidad debe ser un número entero entre 1 y 20.", "warning")
    except InvalidProductIdError:
        flash("No se pudo actualizar el producto seleccionado.", "warning")
    else:
        if updated:
            flash("Carrito actualizado.", "success")
        else:
            flash("El producto no está en el carrito.", "warning")
    return redirect(url_for("cart.view"))


@bp.post("/eliminar")
def remove():
    """Elimina una línea y redirige al carrito."""
    try:
        removed = _service().remove(request.form.get("product_id"))
    except InvalidProductIdError:
        flash("No se pudo eliminar el producto seleccionado.", "warning")
    else:
        if removed:
            flash("Producto eliminado del carrito.", "success")
        else:
            flash("El producto no está en el carrito.", "warning")
    return redirect(url_for("cart.view"))
