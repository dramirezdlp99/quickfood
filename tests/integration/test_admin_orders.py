"""Panel administrativo de pedidos (Ramirez · sección 9.3)."""

import pytest

from app.extensions import db
from app.models import Order


@pytest.fixture()
def admin_logueado(make_user, login):
    make_user(email="admin@test.com", role="admin", name="Admin")
    login("admin@test.com")


def test_admin_ve_el_listado_de_pedidos(client, admin_logueado, make_user, make_order):
    make_order(make_user(email="laura@test.com", name="Laura Gómez"), quantity=2, price=15000)
    html = client.get("/admin/pedidos").get_data(as_text=True)
    assert "Laura Gómez" in html
    assert "$ 30.000" in html
    assert "pendiente" in html


def test_listado_vacio_muestra_mensaje(client, admin_logueado):
    assert "No hay pedidos" in client.get("/admin/pedidos").get_data(as_text=True)


def test_filtro_por_estado(client, admin_logueado, make_user, make_order):
    make_order(make_user(email="a@test.com", name="Cliente Pendiente"), status="pendiente")
    make_order(make_user(email="b@test.com", name="Cliente Entregado"), status="entregado")
    html = client.get("/admin/pedidos?estado=entregado").get_data(as_text=True)
    assert "Cliente Entregado" in html
    assert "Cliente Pendiente" not in html


def test_detalle_corresponde_al_pedido_seleccionado(client, admin_logueado, make_user, make_order):
    make_order(make_user(email="a@test.com", name="Ana"), quantity=1, price=10000, product_name="Pizza")
    pedido_b = make_order(make_user(email="b@test.com", name="Beto"), quantity=3, price=20000, product_name="Sushi")
    html = client.get(f"/admin/pedidos/{pedido_b.id}").get_data(as_text=True)
    assert f"Pedido #{pedido_b.id}" in html
    assert "Beto" in html and "Sushi" in html and "$ 60.000" in html
    assert "Ana" not in html and "Pizza" not in html


def test_detalle_de_pedido_inexistente_devuelve_404(client, admin_logueado):
    assert client.get("/admin/pedidos/9999").status_code == 404


@pytest.mark.parametrize("nuevo_estado", ["preparando", "entregado", "pendiente"])
def test_admin_cambia_estado_a_valores_permitidos(client, admin_logueado, make_user, make_order, nuevo_estado):
    pedido = make_order(make_user(), status="pendiente" if nuevo_estado != "pendiente" else "preparando")
    response = client.post(f"/admin/pedidos/{pedido.id}/estado", data={"status": nuevo_estado})
    assert response.status_code == 302
    assert db.session.get(Order, pedido.id).status == nuevo_estado


@pytest.mark.parametrize("estado_invalido", ["cancelado", "", "ENTREGADO", "<script>"])
def test_admin_no_puede_poner_estados_no_permitidos(client, admin_logueado, make_user, make_order, estado_invalido):
    pedido = make_order(make_user())
    response = client.post(f"/admin/pedidos/{pedido.id}/estado", data={"status": estado_invalido})
    assert response.status_code == 400
    assert db.session.get(Order, pedido.id).status == "pendiente"


def test_cambiar_estado_de_pedido_inexistente_devuelve_404(client, admin_logueado):
    assert client.post("/admin/pedidos/9999/estado", data={"status": "entregado"}).status_code == 404
