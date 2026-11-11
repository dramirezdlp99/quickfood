"""Flujo completo del cliente: catálogo -> menú -> carrito (Mora · sección 9.4)."""

import re

import pytest

from app.extensions import db
from app.models import Product, Restaurant


@pytest.fixture()
def roll(app):
    restaurant = Restaurant(name="Sushi Galeras", cuisine="Japonesa")
    product = Product(restaurant=restaurant, name="Roll California", description="10 piezas", price=28000)
    otro = Product(restaurant=restaurant, name="Ramen de cerdo", price=31000)
    db.session.add_all([restaurant, product, otro])
    db.session.commit()
    return product


def test_del_catalogo_al_carrito_con_el_total_correcto(app, client, roll):
    # Con CSRF activo, como en producción: el token sale del formulario del menú.
    app.config["WTF_CSRF_ENABLED"] = True

    catalogo = client.get("/restaurantes?q=sushi").get_data(as_text=True)
    enlace_menu = re.search(r'href="(/restaurantes/\d+)"', catalogo).group(1)

    menu = client.get(enlace_menu).get_data(as_text=True)
    formulario = re.search(
        rf'<form[^>]*action="(/carrito/agregar)"[^>]*>(?:(?!</form>).)*?value="{roll.id}".*?</form>', menu, re.S
    )
    token = re.search(r'name="csrf_token" value="([^"]+)"', formulario.group(0)).group(1)

    response = client.post(
        formulario.group(1),
        data={"csrf_token": token, "product_id": roll.id, "quantity": "2"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/carrito")

    carrito = client.get("/carrito").get_data(as_text=True)
    total = re.search(r'class="summary-total">.*?<strong>(.*?)</strong>', carrito, re.S).group(1)
    assert "Roll California" in carrito
    assert "Sushi Galeras" in carrito
    assert "Ramen de cerdo" not in carrito
    assert total == "$ 56.000"


def test_agregar_desde_el_menu_sin_token_es_rechazado(app, client, roll):
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post("/carrito/agregar", data={"product_id": roll.id, "quantity": "1"})

    assert response.status_code == 400
    with client.session_transaction() as session:
        assert session.get("cart", {}) == {}
