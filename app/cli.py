"""Comandos de consola: flask --app run <comando>"""

import secrets

import click

from .extensions import db
from .models import Order, OrderItem, Product, Restaurant, User


def register_cli(app) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Crea las tablas de la base de datos."""
        db.create_all()
        click.echo("Base de datos lista.")

    @app.cli.command("create-admin")
    @click.option("--name", default="Administrador")
    @click.option("--email", required=True)
    @click.option("--password", required=True)
    def create_admin(name, email, password):
        """Crea (o actualiza) un usuario administrador."""
        db.create_all()
        user = User.query.filter_by(email=email.lower()).first()
        if user is None:
            user = User(name=name, email=email.lower())
            db.session.add(user)
        user.role = "admin"
        user.set_password(password)
        db.session.commit()
        click.echo(f"Administrador listo: {user.email}")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Carga restaurantes, productos y un pedido de ejemplo (datos ficticios)."""
        db.create_all()
        if Restaurant.query.first() is not None:
            click.echo("Ya existen datos de ejemplo; no se cargó nada.")
            return

        parrilla = Restaurant(name="La Parrilla del Sur", cuisine="Carnes")
        sushi = Restaurant(name="Sushi Galeras", cuisine="Japonesa")
        verde = Restaurant(name="Verde Bowl", cuisine="Saludable")
        db.session.add_all([parrilla, sushi, verde])
        db.session.flush()

        productos = [
            Product(restaurant_id=parrilla.id, name="Hamburguesa clásica", description="Carne 150 g, queso y papas", price=22000),
            Product(restaurant_id=parrilla.id, name="Costillas BBQ", description="Media libra con ensalada", price=34000),
            Product(restaurant_id=sushi.id, name="Roll California", description="10 piezas", price=28000),
            Product(restaurant_id=sushi.id, name="Ramen de cerdo", description="Caldo tonkotsu", price=31000),
            Product(restaurant_id=verde.id, name="Bowl de pollo", description="Quinoa, pollo y aguacate", price=24000),
        ]
        db.session.add_all(productos)

        # Cliente de ejemplo con contraseña aleatoria (solo para tener un pedido de muestra).
        cliente = User(name="Cliente Demo", email="cliente.demo@quickfood.test", role="cliente")
        cliente.set_password(secrets.token_urlsafe(16))
        db.session.add(cliente)
        db.session.flush()

        pedido = Order(user_id=cliente.id, status="pendiente")
        pedido.items = [
            OrderItem(product_id=productos[0].id, quantity=2, unit_price=productos[0].price),
            OrderItem(product_id=productos[2].id, quantity=1, unit_price=productos[2].price),
        ]
        pedido.total = sum(item.subtotal for item in pedido.items)
        db.session.add(pedido)
        db.session.commit()
        click.echo("Datos de ejemplo cargados: 3 restaurantes, 5 productos y 1 pedido.")
