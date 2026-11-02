"""Pruebas unitarias de los servicios y objetos del carrito."""

from dataclasses import FrozenInstanceError

import pytest

from app.extensions import db
from app.models import Product, Restaurant
from app.services.cart_service import (
    CartLine,
    CartStorage,
    CartService,
    CartSummary,
    InvalidQuantityError,
    QuantityValidator,
)


@pytest.fixture()
def product(app):
    """Crea un producto cuyo precio permite verificar los cálculos."""
    restaurant = Restaurant(name="Restaurante de prueba", cuisine="Rápida")
    product = Product(restaurant=restaurant, name="Hamburguesa", price=12500)
    db.session.add_all([restaurant, product])
    db.session.commit()
    return product


@pytest.mark.parametrize("value", [0, -1, 21, "abc"])
def test_validador_rechaza_cantidades_fuera_del_rango_o_invalidas(value):
    with pytest.raises(InvalidQuantityError):
        QuantityValidator.validate(value)


def test_validador_convierte_cantidad_entera_en_texto():
    assert QuantityValidator.validate("2") == 2


def test_almacen_normaliza_claves_enteras_y_texto():
    session = {"cart": {"5": 2, 6: 3, "inválida": 4}}
    storage = CartStorage(session)

    assert storage.read() == {5: 2, 6: 3}
    assert session["cart"] == {"5": 2, "6": 3}


def test_servicio_agrega_suma_actualiza_y_elimina_producto(app, product):
    with app.test_request_context():
        from flask import session

        service = CartService(CartStorage(session))
        service.add(product.id, "2")
        service.add(str(product.id), 1)
        assert service.storage.read() == {product.id: 3}

        service.update(product.id, "2")
        assert service.storage.read() == {product.id: 2}

        service.remove(str(product.id))
        assert service.storage.read() == {}


def test_resumen_descarta_producto_inexistente_y_usa_precio_de_bd(app, product):
    with app.test_request_context():
        from flask import session

        session["cart"] = {str(product.id): 2, "999999": 4}
        summary = CartService(CartStorage(session)).summary()

        assert isinstance(summary, CartSummary)
        assert len(summary.lines) == 1
        assert isinstance(summary.lines[0], CartLine)
        assert summary.lines[0].quantity == 2
        assert summary.lines[0].subtotal == 25000
        assert summary.total == 25000
        assert CartStorage(session).read() == {product.id: 2}


def test_linea_y_resumen_son_dataclasses_inmutables(product):
    line = CartLine(product=product, quantity=2, subtotal=25000)
    summary = CartSummary(lines=(line,), total=25000)

    assert summary.lines == (line,)
    with pytest.raises(FrozenInstanceError):
        summary.total = 1
