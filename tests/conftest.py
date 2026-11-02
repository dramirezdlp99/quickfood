"""Fixtures compartidas por todas las pruebas.

Cada prueba recibe una aplicación nueva con una base de datos SQLite en
memoria, así las pruebas no dependen unas de otras.
"""

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Order, OrderItem, Product, Restaurant, User

DEFAULT_PASSWORD = "Prueba123*"


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    def _make_user(email="cliente@test.com", role="cliente", name="Cliente Prueba", password=DEFAULT_PASSWORD):
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        return user

    return _make_user


@pytest.fixture()
def login(client):
    def _login(email, password=DEFAULT_PASSWORD):
        return client.post("/auth/ingresar", data={"email": email, "password": password})

    return _login


@pytest.fixture()
def make_order(app):
    """Crea un restaurante, un producto y un pedido de 2 unidades para el usuario dado."""

    def _make_order(user, quantity=2, price=15000, status="pendiente", product_name="Hamburguesa"):
        restaurant = Restaurant(name="Restaurante Prueba", cuisine="Rápida")
        product = Product(restaurant=restaurant, name=product_name, price=price)
        order = Order(user=user, status=status, total=quantity * price)
        order.items = [OrderItem(product=product, quantity=quantity, unit_price=price)]
        _db.session.add_all([restaurant, product, order])
        _db.session.commit()
        return order

    return _make_order
