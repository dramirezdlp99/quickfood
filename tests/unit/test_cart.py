"""Pruebas iniciales del carrito (casos 1 a 5 de la propuesta)."""

import re
from pathlib import Path

import pytest
from sqlalchemy import event

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


def _count_queries_viewing_cart(client, product_ids):
    """Cuenta las consultas SQL que hace GET /carrito con esos productos."""
    statements = []

    def _record(*_args):
        statements.append(1)

    with client.session_transaction() as session:
        session["cart"] = {str(product_id): 1 for product_id in product_ids}
    db.session.expire_all()
    event.listen(db.engine, "before_cursor_execute", _record)
    try:
        response = client.get("/carrito")
    finally:
        event.remove(db.engine, "before_cursor_execute", _record)
    assert response.status_code == 200
    return len(statements)


def test_ver_carrito_no_hace_una_consulta_por_restaurante(client, app):
    products = [
        Product(restaurant=Restaurant(name=f"Restaurante {n}", cuisine="Rápida"), name=f"Plato {n}", price=1000)
        for n in range(3)
    ]
    db.session.add_all(products)
    db.session.commit()
    ids = [product.id for product in products]

    assert _count_queries_viewing_cart(client, ids) == _count_queries_viewing_cart(client, ids[:1])


def test_contenedores_con_aria_label_tienen_rol(client, producto):
    """ARIA no permite aria-label en un div genérico; los lectores lo ignoran."""
    with client.session_transaction() as session:
        session["cart"] = {str(producto.id): 2}
    html = client.get("/carrito").get_data(as_text=True)

    assert re.search(r"<div(?![^>]*\brole=)[^>]*\baria-label=", html) is None
    assert 'role="group" aria-label="Cantidad de Hamburguesa"' in html


def test_botones_se_reactivan_al_volver_desde_la_cache_del_navegador():
    script = (Path(__file__).parents[2] / "app" / "static" / "js" / "cart.js").read_text(encoding="utf-8")

    assert '"pageshow"' in script


@pytest.mark.parametrize("cart", [{}, None])
def test_enlace_seguir_comprando_lleva_al_inicio_sin_modulo_de_restaurantes(client, producto, cart):
    with client.session_transaction() as session:
        session["cart"] = cart if cart is not None else {str(producto.id): 1}
    html = client.get("/carrito").get_data(as_text=True)

    assert re.search(r'href="/"[^>]*>\s*(Seguir comprando|Explorar restaurantes)', html)


def test_formulario_de_cantidad_tiene_boton_actualizar_visible(client, producto):
    """Sin autoenvío, el usuario necesita un botón explícito para guardar la cantidad escrita."""
    with client.session_transaction() as session:
        session["cart"] = {str(producto.id): 2}
    html = client.get("/carrito").get_data(as_text=True)

    form = re.search(r'<form[^>]*quantity-form[^>]*>(.*?)</form>', html, re.S).group(1)
    assert 'name="quantity"' in form
    button = re.search(r'<button[^>]*type="submit"[^>]*>(.*?)</button>', form, re.S)
    assert button is not None
    assert 'aria-label="Actualizar cantidad de Hamburguesa"' in button.group(0)
    assert "visually-hidden" not in button.group(0)
    assert "Actualizar" in button.group(1)
