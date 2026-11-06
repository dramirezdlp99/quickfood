"""Panel administrativo: consulta de pedidos y cambio de estado (módulo de Ramirez)."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..extensions import db
from ..models import Order
from ..services.auth_service import admin_required
from ..services.cart_service import MAX_DB_ID

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/pedidos")
@admin_required
def orders():
    status_filter = request.args.get("estado", "")
    query = Order.query.order_by(Order.created_at.desc())
    if status_filter in Order.STATUSES:
        query = query.filter_by(status=status_filter)
    else:
        status_filter = ""
    return render_template(
        "admin/orders.html", orders=query.all(), statuses=Order.STATUSES, status_filter=status_filter
    )


def _get_order_or_404(order_id: int) -> Order:
    """Busca el pedido; un id fuera de rango o inexistente responde 404 (no 500)."""
    order = db.session.get(Order, order_id) if 1 <= order_id <= MAX_DB_ID else None
    if order is None:
        abort(404)
    return order


@bp.get("/pedidos/<int:order_id>")
@admin_required
def order_detail(order_id: int):
    order = _get_order_or_404(order_id)
    return render_template("admin/order_detail.html", order=order, statuses=Order.STATUSES)


@bp.post("/pedidos/<int:order_id>/estado")
@admin_required
def update_status(order_id: int):
    order = _get_order_or_404(order_id)

    new_status = request.form.get("status", "")
    if new_status not in Order.STATUSES:
        abort(400)  # solo se aceptan: pendiente, preparando, entregado

    order.status = new_status
    db.session.commit()
    flash(f"El pedido #{order.id} ahora está «{new_status}».", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))
