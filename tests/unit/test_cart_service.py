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
    InvalidProductIdError,
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


@pytest.mark.parametrize("value", [True, False, None, 2.5, [], " ", "1.5", "-2"])
def test_validador_rechaza_booleanos_tipos_no_soportados_y_texto_no_entero(value):
    with pytest.raises(InvalidQuantityError):
        QuantityValidator.validate(value)


@pytest.mark.parametrize("raw_cart", ["corrupto", ["5", 2], None])
def test_almacen_reinicia_carrito_corrupto_en_la_sesion(raw_cart):
    session = {"cart": raw_cart}

    assert CartStorage(session).read() == {}
    assert session["cart"] == {}


def test_almacen_descarta_cantidades_e_ids_no_positivos():
    session = {"cart": {"5": 0, "6": -1, "0": 2, "7": 1}}

    assert CartStorage(session).read() == {7: 1}


def test_almacen_no_escribe_la_sesion_si_solo_lee_un_carrito_valido():
    """Leer no debe marcar la sesión como modificada (evita Set-Cookie en cada GET)."""
    empty_session = {}
    valid_session = {"cart": {"5": 2}}

    CartStorage(empty_session).read()
    CartStorage(valid_session).read()

    assert "cart" not in empty_session
    assert valid_session == {"cart": {"5": 2}}


@pytest.mark.parametrize("product_id", ["abc", "0", "-1", None])
def test_servicio_rechaza_ids_de_producto_invalidos(app, product_id):
    with app.test_request_context():
        from flask import session

        with pytest.raises(InvalidProductIdError):
            CartService(CartStorage(session)).remove(product_id)


@pytest.mark.parametrize("zero", [0, "0", " 0 ", "00"])
def test_actualizar_con_cero_en_cualquier_formato_elimina_la_linea(app, product, zero):
    with app.test_request_context():
        from flask import session

        service = CartService(CartStorage(session))
        service.add(product.id, 2)

        assert service.update(product.id, zero) is True
        assert service.storage.read() == {}


def test_agregar_por_encima_del_maximo_avisa_el_limite_por_producto(app, product):
    with app.test_request_context():
        from flask import session

        service = CartService(CartStorage(session))
        service.add(product.id, 19)

        with pytest.raises(InvalidQuantityError, match="máximo 20 unidades"):
            service.add(product.id, 2)
        assert service.storage.read() == {product.id: 19}


def test_agregar_valida_la_cantidad_antes_de_consultar_el_producto(app):
    """La validación barata va primero: con ambos datos inválidos gana la cantidad."""
    with app.test_request_context():
        from flask import session

        with pytest.raises(InvalidQuantityError):
            CartService(CartStorage(session)).add("999999", "abc")
