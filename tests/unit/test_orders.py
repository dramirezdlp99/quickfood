"""Pruebas del servicio de pedidos (casos 6 a 9 de la sección 9.2)."""

import pytest
from flask import session as request_session
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Order, Product, Restaurant
from app.services.cart_service import CartService, CartStorage
from app.services.order_service import (
    CheckoutToken,
    EmptyCartError,
    InvalidCheckoutTokenError,
    OrderPlacer,
    OrderQueries,
    PriceChangedError,
)


@pytest.fixture()
def products(app):
    """Dos productos con precios conocidos."""
    restaurant = Restaurant(name="Restaurante de prueba", cuisine="Rápida")
    burger = Product(restaurant=restaurant, name="Hamburguesa", price=12500)
    soda = Product(restaurant=restaurant, name="Gaseosa", price=4000)
    db.session.add_all([restaurant, burger, soda])
    db.session.commit()
    return burger, soda


@pytest.fixture()
def customer(make_user):
    return make_user(email="laura@test.com", name="Laura")


@pytest.fixture()
def cart(app):
    """Carrito sobre la sesión de una solicitud de prueba."""
    with app.test_request_context():
        yield CartService(CartStorage(request_session))


def test_token_de_confirmacion_es_de_un_solo_uso():
    session = {}
    checkout = CheckoutToken(session)
    token = checkout.issue(total=25000)

    assert checkout.consume(token) == 25000
    with pytest.raises(InvalidCheckoutTokenError):
        checkout.consume(token)


def test_tokens_emitidos_son_distintos_y_el_nuevo_reemplaza_al_anterior():
    session = {}
    checkout = CheckoutToken(session)
    first = checkout.issue(total=1000)
    second = checkout.issue(total=2000)

    assert first != second
    with pytest.raises(InvalidCheckoutTokenError):
        checkout.consume(first)


@pytest.mark.parametrize("submitted", [None, "", "token-falso", "ñandú", 123])
def test_token_invalido_se_rechaza_y_descarta_el_vigente(submitted):
    session = {}
    checkout = CheckoutToken(session)
    token = checkout.issue(total=1000)

    with pytest.raises(InvalidCheckoutTokenError):
        checkout.consume(submitted)
    with pytest.raises(InvalidCheckoutTokenError):
        checkout.consume(token)


@pytest.mark.parametrize("stored", [None, "corrupto", {"token": "abc"}, {"total": 5}])
def test_token_corrupto_en_la_sesion_se_rechaza(stored):
    session = {} if stored is None else {CheckoutToken.KEY: stored}

    with pytest.raises(InvalidCheckoutTokenError):
        CheckoutToken(session).consume("abc")


def test_caso6_no_se_puede_confirmar_un_carrito_vacio(cart, customer):
    with pytest.raises(EmptyCartError):
        OrderPlacer(cart).place(customer.id, expected_total=0)
    assert Order.query.count() == 0


def test_caso7_total_se_calcula_con_el_precio_almacenado_al_confirmar(cart, customer, products):
    burger, _ = products
    cart.add(burger.id, 2)
    burger.price = 15000  # el precio cambia en la BD después de agregar
    db.session.commit()

    order = OrderPlacer(cart).place(customer.id, expected_total=30000)

    assert order.total == 30000
    assert order.items[0].unit_price == 15000


def test_caso7_si_el_precio_cambio_despues_del_resumen_no_se_crea_el_pedido(cart, customer, products):
    burger, _ = products
    cart.add(burger.id, 2)
    expected = cart.summary().total  # 25000: lo que el usuario vio
    burger.price = 15000
    db.session.commit()

    with pytest.raises(PriceChangedError):
        OrderPlacer(cart).place(customer.id, expected_total=expected)
    assert Order.query.count() == 0
    assert cart.storage.read() == {burger.id: 2}


def test_caso8_pedido_valido_se_guarda_con_items_total_y_estado_inicial(cart, customer, products):
    burger, soda = products
    cart.add(burger.id, 2)
    cart.add(soda.id, 3)

    order = OrderPlacer(cart).place(customer.id, expected_total=37000)

    saved = db.session.get(Order, order.id)
    assert saved.user_id == customer.id
    assert saved.total == 37000
    assert saved.status == "pendiente"
    assert {(item.product_id, item.quantity, item.unit_price) for item in saved.items} == {
        (burger.id, 2, 12500),
        (soda.id, 3, 4000),
    }
    assert cart.storage.read() == {}


def test_si_falla_la_base_de_datos_no_queda_pedido_y_se_conserva_el_carrito(
    cart, customer, products, monkeypatch
):
    burger, _ = products
    cart.add(burger.id, 1)

    def _fail():
        raise SQLAlchemyError("fallo simulado")

    monkeypatch.setattr(db.session, "commit", _fail)
    with pytest.raises(SQLAlchemyError):
        OrderPlacer(cart).place(customer.id, expected_total=12500)
    monkeypatch.undo()

    assert Order.query.count() == 0
    assert cart.storage.read() == {burger.id: 1}


def test_lista_solo_los_pedidos_del_usuario_del_mas_reciente_al_mas_antiguo(make_user, make_order):
    laura = make_user(email="laura@test.com", name="Laura")
    pedro = make_user(email="pedro@test.com", name="Pedro")
    first = make_order(laura)
    make_order(pedro)
    second = make_order(laura)

    assert OrderQueries.list_for_user(laura.id) == [second, first]


def test_obtiene_el_pedido_solo_si_es_del_usuario(make_user, make_order):
    laura = make_user(email="laura@test.com", name="Laura")
    pedro = make_user(email="pedro@test.com", name="Pedro")
    order = make_order(laura)

    assert OrderQueries.get_for_user(order.id, laura.id) == order
    assert OrderQueries.get_for_user(order.id, pedro.id) is None


@pytest.mark.parametrize("order_id", [999999, 0, -1, 2**31, 10**25])
def test_pedido_inexistente_o_fuera_de_rango_devuelve_none(customer, order_id):
    assert OrderQueries.get_for_user(order_id, customer.id) is None
