"""Consultas del catálogo: restaurantes, búsqueda y menús."""

from typing import Any

from sqlalchemy import func, or_

from ..extensions import db
from ..models import Product, Restaurant

MAX_SEARCH_LENGTH = 60
MAX_RESTAURANT_ID = 2**31 - 1  # límite de INTEGER en SQLite/PostgreSQL
LIKE_ESCAPE = "\\"


def normalize_search(value: Any) -> str:
    """Quita espacios y recorta el texto buscado a la longitud máxima."""
    if not isinstance(value, str):
        return ""
    return value.strip()[:MAX_SEARCH_LENGTH].strip()


def _like_pattern(term: str) -> str:
    """Escapa los comodines de LIKE para buscarlos como texto normal."""
    escaped = (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )
    return f"%{escaped}%"


def list_restaurants(search: Any = None) -> list[Restaurant]:
    """Lista los restaurantes por nombre; filtra por nombre o tipo de comida si hay búsqueda."""
    query = Restaurant.query
    term = normalize_search(search)
    if term:
        pattern = _like_pattern(term)
        query = query.filter(
            or_(
                Restaurant.name.ilike(pattern, escape=LIKE_ESCAPE),
                Restaurant.cuisine.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    return query.order_by(func.lower(Restaurant.name), Restaurant.id).all()


def get_restaurant(restaurant_id: int) -> Restaurant | None:
    """Devuelve el restaurante, o None si no existe o el id está fuera de rango."""
    if not 1 <= restaurant_id <= MAX_RESTAURANT_ID:
        return None
    return db.session.get(Restaurant, restaurant_id)


def list_products(restaurant_id: int) -> list[Product]:
    """Lista únicamente los productos del restaurante indicado."""
    return (
        Product.query.filter_by(restaurant_id=restaurant_id)
        .order_by(func.lower(Product.name), Product.id)
        .all()
    )
