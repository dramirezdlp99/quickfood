"""Rutas del catálogo: listado de restaurantes, búsqueda y menú."""

from flask import Blueprint, abort, render_template, request

from ..services.cart_service import MAX_QUANTITY
from ..services.catalog_service import (
    MAX_SEARCH_LENGTH,
    get_restaurant,
    list_products,
    list_restaurants,
    normalize_search,
)

bp = Blueprint("restaurants", __name__, url_prefix="/restaurantes")


@bp.get("")
def index():
    """Muestra los restaurantes, filtrados si llega el parámetro ?q=."""
    search = normalize_search(request.args.get("q"))
    return render_template(
        "restaurants/index.html",
        restaurants=list_restaurants(search),
        search=search,
        max_search_length=MAX_SEARCH_LENGTH,
    )


@bp.get("/<int:restaurant_id>")
def menu(restaurant_id: int):
    """Muestra el menú de un restaurante; 404 si no existe."""
    restaurant = get_restaurant(restaurant_id)
    if restaurant is None:
        abort(404)
    return render_template(
        "restaurants/menu.html",
        restaurant=restaurant,
        products=list_products(restaurant.id),
        max_quantity=MAX_QUANTITY,
    )
