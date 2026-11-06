"""Flujo completo con CSRF activo: catálogo -> menú -> carrito -> confirmar -> Mis pedidos -> panel admin.

Daniers · sección 9.2 (casos 8 y 10). Continúa el recorrido de test_catalog_flow.py.
"""

import re

import pytest
from flask import g

from app.extensions import db
from app.models import Order, Product, Restaurant

PASSWORD = "Prueba123*"
TOKEN = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture()
def roll(app):
    restaurant = Restaurant(name="Sushi Galeras", cuisine="Japonesa")
    product = Product(restaurant=restaurant, name="Roll California", description="10 piezas", price=28000)
    db.session.add_all([restaurant, product])
    db.session.commit()
    return product


@pytest.fixture()
def users(app, make_user):
    app.config["WTF_CSRF_ENABLED"] = True  # como en producción
    make_user(email="laura@test.com", name="Laura Gómez")
    make_user(email="admin@test.com", name="Admin", role="admin")


def _token(html):
    return TOKEN.search(html).group(1)


def _page(client, url):
    """GET de una página con formulario.

    El fixture app de conftest mantiene un app_context abierto, así que flask.g se comparte
    entre peticiones y Flask-WTF reutilizaría el token CSRF de otra sesión (por ejemplo, el de
    antes de iniciar sesión, o el del otro cliente). En producción cada petición tiene su g.
    """
    g.pop("csrf_token", None)
    return client.get(url).get_data(as_text=True)


def _log_in(client, email):
    token = _token(_page(client, "/auth/ingresar"))
    response = client.post("/auth/ingresar", data={"csrf_token": token, "email": email, "password": PASSWORD})
    assert response.status_code == 302


def _customer_confirms_order(client, product):
    """Recorre catálogo, menú y carrito, y confirma; devuelve el id del pedido."""
    catalog = _page(client, "/restaurantes?q=sushi")
    menu = _page(client, re.search(r'href="(/restaurantes/\d+)"', catalog).group(1))
    form = re.search(rf'<form[^>]*action="/carrito/agregar"[^>]*>(?:(?!</form>).)*?value="{product.id}".*?</form>', menu, re.S)
    client.post("/carrito/agregar", data={"csrf_token": _token(form.group(0)), "product_id": product.id, "quantity": "2"})

    cart = client.get("/carrito").get_data(as_text=True)
    summary = _page(client, re.search(r'href="(/pedidos/confirmar)"', cart).group(1))
    assert "$ 56.000" in summary
    response = client.post(
        "/pedidos/confirmar",
        data={
            "csrf_token": _token(summary),
            "checkout_token": re.search(r'name="checkout_token" value="([^"]+)"', summary).group(1),
        },
    )
    assert response.status_code == 302
    return int(re.search(r"/pedidos/(\d+)$", response.headers["Location"]).group(1))


def _admin_sets_status(admin, order_id, status):
    detail = _page(admin, f"/admin/pedidos/{order_id}")
    return admin.post(f"/admin/pedidos/{order_id}/estado", data={"csrf_token": _token(detail), "status": status})


def test_flujo_completo_del_catalogo_al_cambio_de_estado(app, users, roll):
    customer, admin = app.test_client(), app.test_client()
    _log_in(customer, "laura@test.com")

    order_id = _customer_confirms_order(customer, roll)

    mine = customer.get("/pedidos").get_data(as_text=True)
    assert f"#{order_id}" in mine
    assert "qf-status-pendiente" in mine
    with customer.session_transaction() as session:
        assert session.get("cart") == {}

    _log_in(admin, "admin@test.com")
    panel = admin.get("/admin/pedidos").get_data(as_text=True)
    assert "Laura Gómez" in panel
    assert "$ 56.000" in panel

    assert _admin_sets_status(admin, order_id, "preparando").status_code == 302
    detail = customer.get(f"/pedidos/{order_id}").get_data(as_text=True)
    assert "qf-status-preparando" in detail


@pytest.mark.parametrize("invalid", ["cancelado", "", "PREPARANDO", "pendiente'; DROP TABLE orders;--"])
def test_caso10_el_estado_solo_cambia_a_valores_permitidos(app, users, roll, invalid):
    customer, admin = app.test_client(), app.test_client()
    _log_in(customer, "laura@test.com")
    order_id = _customer_confirms_order(customer, roll)
    _log_in(admin, "admin@test.com")

    assert _admin_sets_status(admin, order_id, invalid).status_code == 400
    db.session.expire_all()
    assert db.session.get(Order, order_id).status == "pendiente"
    assert "qf-status-pendiente" in customer.get(f"/pedidos/{order_id}").get_data(as_text=True)

    for status in Order.STATUSES:
        assert _admin_sets_status(admin, order_id, status).status_code == 302
        assert f"qf-status-{status}" in customer.get(f"/pedidos/{order_id}").get_data(as_text=True)


def test_cliente_no_puede_cambiar_el_estado_de_su_propio_pedido(app, users, roll):
    customer = app.test_client()
    _log_in(customer, "laura@test.com")
    order_id = _customer_confirms_order(customer, roll)
    mine = _page(customer, f"/pedidos/{order_id}")

    response = customer.post(f"/admin/pedidos/{order_id}/estado", data={"csrf_token": _token(mine), "status": "entregado"})

    assert response.status_code == 403
    db.session.expire_all()
    assert db.session.get(Order, order_id).status == "pendiente"
