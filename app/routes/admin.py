"""Panel administrativo: consulta de pedidos y cambio de estado (módulo de Ramirez)."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..extensions import db
from ..models import Order
from ..services.auth_service import admin_required

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


@bp.get("/pedidos/<int:order_id>")
@admin_required
def order_detail(order_id: int):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    return render_template("admin/order_detail.html", order=order, statuses=Order.STATUSES)


@bp.post("/pedidos/<int:order_id>/estado")
@admin_required
def update_status(order_id: int):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)

    new_status = request.form.get("status", "")
    if new_status not in Order.STATUSES:
        abort(400)  # solo se aceptan: pendiente, preparando, entregado

    order.status = new_status
    db.session.commit()
    flash(f"El pedido #{order.id} ahora está «{new_status}».", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))
