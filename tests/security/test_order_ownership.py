"""Seguridad de pedidos: sesión obligatoria y cada usuario ve solo sus pedidos."""

import pytest

ROUTES = [("get", "/pedidos"), ("get", "/pedidos/1"), ("get", "/pedidos/confirmar"), ("post", "/pedidos/confirmar")]


@pytest.fixture()
def laura_order(make_user, make_order):
    """Pedido de Laura; Pedro es otro cliente sin pedidos."""
    make_user(email="pedro@test.com", name="Pedro")
    return make_order(make_user(email="laura@test.com", name="Laura"))


@pytest.mark.parametrize("method, url", ROUTES)
def test_sin_sesion_redirige_al_login(client, method, url):
    response = getattr(client, method)(url)

    assert response.status_code == 302
    assert "/auth/ingresar?next=" in response.headers["Location"]


def test_usuario_no_puede_ver_el_pedido_de_otro(client, login, laura_order):
    login("pedro@test.com")

    assert client.get(f"/pedidos/{laura_order.id}").status_code == 404


def test_lista_de_pedidos_no_muestra_pedidos_de_otro(client, login, laura_order):
    login("pedro@test.com")
    html = client.get("/pedidos").get_data(as_text=True)

    assert f"/pedidos/{laura_order.id}" not in html
    assert "Aún no tienes pedidos" in html


def test_duenio_si_ve_su_pedido(client, login, laura_order):
    login("laura@test.com")

    assert client.get(f"/pedidos/{laura_order.id}").status_code == 200


@pytest.mark.parametrize("order_id", ["0", "99999", "1" + "0" * 25])
def test_pedido_inexistente_o_id_gigante_responde_404_sin_error_500(client, login, laura_order, order_id):
    login("laura@test.com")

    assert client.get(f"/pedidos/{order_id}").status_code == 404


@pytest.mark.parametrize("method, url", [("get", "/admin/pedidos/{id}"), ("post", "/admin/pedidos/{id}/estado")])
@pytest.mark.parametrize("order_id", ["0", "1" + "0" * 25])
def test_admin_con_id_fuera_de_rango_responde_404_sin_error_500(client, make_user, login, method, url, order_id):
    make_user(email="admin@test.com", role="admin", name="Admin")
    login("admin@test.com")

    response = getattr(client, method)(url.format(id=order_id), data={"status": "preparando"})

    assert response.status_code == 404
