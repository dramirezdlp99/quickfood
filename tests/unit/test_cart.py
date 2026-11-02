"""Pruebas iniciales del carrito (casos 1 a 5 de la propuesta)."""

import re
from pathlib import Path

import pytest

from app.extensions import db
from app.models import Product, Restaurant


@pytest.fixture()
def producto(app):
    """Crea un producto de prueba con precio conocido."""
    restaurant = Restaurant(name="Restaurante de prueba", cuisine="Rápida")
    product = Product(restaurant=restaurant, name="Hamburguesa", price=12500)
    db.session.add_all([restaurant, product])
    db.session.commit()
    return product


def test_agregar_producto_aumenta_contenido_del_carrito(client, producto):
    response = client.post(
        "/carrito/agregar", data={"product_id": producto.id, "quantity": "1"}
    )

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["cart"] == {str(producto.id): 1}


def test_agregar_dos_unidades_calcula_subtotal_correcto(client, producto):
    client.post(
        "/carrito/agregar", data={"product_id": producto.id, "quantity": "2"}
    )

    response = client.get("/carrito")
    assert response.status_code == 200
    assert "$ 25.000" in response.get_data(as_text=True)


def test_disminuir_o_eliminar_unidad_actualiza_total(client, producto):
    client.post(
        "/carrito/agregar", data={"product_id": producto.id, "quantity": "2"}
    )
    response = client.post(
        "/carrito/actualizar", data={"product_id": producto.id, "quantity": "1"}
    )

    assert response.status_code == 302
    response = client.get("/carrito")
    assert "$ 12.500" in response.get_data(as_text=True)
    assert "$ 25.000" not in response.get_data(as_text=True)

    response = client.post(
        "/carrito/actualizar", data={"product_id": producto.id, "quantity": "0"}
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session.get("cart", {}) == {}


@pytest.mark.parametrize("quantity", ["0", "-1", "abc"])
def test_rechazar_cantidad_cero_negativa_o_no_entera(client, producto, quantity):
    response = client.post(
        "/carrito/agregar",
        data={"product_id": producto.id, "quantity": quantity},
    )

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session.get("cart", {}) == {}


@pytest.mark.parametrize("submitted_price", ["-1", "999999"])
def test_ignorar_precio_manipulado_y_usar_precio_de_base_de_datos(
    client, producto, submitted_price
):
    client.post(
        "/carrito/agregar",
        data={
            "product_id": producto.id,
            "quantity": "1",
            "price": submitted_price,
        },
    )

    response = client.get("/carrito")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "$ 12.500" in body
    assert "$ -1" not in body
    assert "$ 999.999" not in body


def test_actualizar_con_cantidad_invalida_avisa_y_conserva_carrito(client, producto):
    with client.session_transaction() as session:
        session["cart"] = {str(producto.id): 2}

    response = client.post(
        "/carrito/actualizar",
        data={"product_id": producto.id, "quantity": "abc"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "La cantidad debe ser un número entero entre 1 y 20." in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert session["cart"] == {str(producto.id): 2}


def test_actualizar_producto_inexistente_avisa_y_conserva_carrito(client, producto):
    with client.session_transaction() as session:
        session["cart"] = {str(producto.id): 2}

    response = client.post(
        "/carrito/actualizar",
        data={"product_id": "999999", "quantity": "1"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "No se pudo actualizar el producto seleccionado." in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert session["cart"] == {str(producto.id): 2}


def test_actualizar_producto_que_no_esta_en_carrito_avisa_y_no_lo_agrega(client, producto):
    response = client.post(
        "/carrito/actualizar",
        data={"product_id": producto.id, "quantity": "1"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "no está en el carrito" in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert session.get("cart", {}) == {}


def test_eliminar_producto_inexistente_avisa_y_conserva_carrito(client, producto):
    with client.session_transaction() as session:
        session["cart"] = {str(producto.id): 2}

    response = client.post(
        "/carrito/eliminar", data={"product_id": "999999"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert "No se pudo eliminar el producto seleccionado." in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert session["cart"] == {str(producto.id): 2}


def test_campo_cantidad_no_se_envia_solo_al_cambiar(client, producto):
    """WCAG 3.2.2: cambiar el valor no debe recargar la página sin que el usuario lo pida."""
    script = (Path(__file__).parents[2] / "app" / "static" / "js" / "cart.js").read_text(encoding="utf-8")
    with client.session_transaction() as session:
        session["cart"] = {str(producto.id): 2}
    html = client.get("/carrito").get_data(as_text=True)

    assert "requestSubmit" not in script
    assert "js-quantity-input" not in html


@pytest.mark.parametrize("url", ["/carrito/agregar", "/carrito/actualizar", "/carrito/eliminar"])
def test_post_sin_csrf_token_es_rechazado(app, client, producto, url):
    app.config["WTF_CSRF_ENABLED"] = True
    with client.session_transaction() as session:
        session["cart"] = {str(producto.id): 2}

    response = client.post(url, data={"product_id": producto.id, "quantity": "1"})

    assert response.status_code == 400
    with client.session_transaction() as session:
        assert session["cart"] == {str(producto.id): 2}


def test_post_con_csrf_token_de_la_plantilla_es_aceptado(app, client, producto):
    app.config["WTF_CSRF_ENABLED"] = True
    with client.session_transaction() as session:
        session["cart"] = {str(producto.id): 2}
    html = client.get("/carrito").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

    response = client.post(
        "/carrito/actualizar",
        data={"csrf_token": token, "product_id": producto.id, "quantity": "3"},
    )

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["cart"] == {str(producto.id): 3}


@pytest.mark.parametrize("url", ["/carrito/agregar", "/carrito/actualizar", "/carrito/eliminar"])
@pytest.mark.parametrize("product_id",["9" * 25, str(2**31)])
def test_product_id_fuera_de_rango_avisa_sin_error_500(client, producto, url, product_id):
    response = client.post(
        url, data={"product_id": product_id, "quantity": "1"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert "No se pudo" in response.get_data(as_text=True)


def test_eliminar_producto_que_no_esta_en_carrito_avisa_y_no_rompe_carrito(client, producto):
    response = client.post(
        "/carrito/eliminar", data={"product_id": producto.id}, follow_redirects=True
    )

    assert response.status_code == 200
    assert "no está en el carrito" in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert session.get("cart", {}) == {}
