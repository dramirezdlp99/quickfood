"""Control de acceso a rutas administrativas (Ramirez · sección 9.3)."""

import pytest

RUTAS_ADMIN_GET = ["/admin/pedidos", "/admin/pedidos/1"]


@pytest.mark.parametrize("ruta", RUTAS_ADMIN_GET)
def test_usuario_no_autenticado_es_enviado_al_login(client, ruta):
    response = client.get(ruta)
    assert response.status_code == 302
    assert "/auth/ingresar" in response.headers["Location"]


@pytest.mark.parametrize("ruta", RUTAS_ADMIN_GET)
def test_cliente_no_puede_entrar_a_rutas_admin(client, make_user, login, make_order, ruta):
    cliente = make_user(email="cliente@test.com")
    make_order(cliente)
    login("cliente@test.com")
    assert client.get(ruta).status_code == 403


def test_usuario_no_autenticado_no_puede_cambiar_estado(client, make_user, make_order):
    pedido = make_order(make_user())
    response = client.post(f"/admin/pedidos/{pedido.id}/estado", data={"status": "entregado"})
    assert response.status_code == 302
    assert pedido.status == "pendiente"


def test_cliente_no_puede_cambiar_estado(client, make_user, login, make_order):
    cliente = make_user(email="cliente@test.com")
    pedido = make_order(cliente)
    login("cliente@test.com")
    response = client.post(f"/admin/pedidos/{pedido.id}/estado", data={"status": "entregado"})
    assert response.status_code == 403
    assert pedido.status == "pendiente"


def test_admin_si_puede_entrar(client, make_user, login):
    make_user(email="admin@test.com", role="admin")
    login("admin@test.com")
    assert client.get("/admin/pedidos").status_code == 200
