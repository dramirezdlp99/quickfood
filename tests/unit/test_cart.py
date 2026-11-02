"""Pruebas iniciales del carrito (casos 1 a 5 de la propuesta)."""

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
