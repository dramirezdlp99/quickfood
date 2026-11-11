"""Pruebas del catálogo: restaurantes, búsqueda y menús."""

import re

import pytest

from app.extensions import db
from app.models import Product, Restaurant
from app.services.catalog_service import MAX_SEARCH_LENGTH, normalize_search


@pytest.fixture()
def catalogo(app):
    """Crea dos restaurantes con productos y uno sin productos."""
    parrilla = Restaurant(name="La Parrilla del Sur", cuisine="Carnes")
    sushi = Restaurant(name="Sushi Galeras", cuisine="Japonesa")
    vacio = Restaurant(name="Cocina Vacía", cuisine="Casera")
    hamburguesa = Product(restaurant=parrilla, name="Hamburguesa clásica", description="Carne y papas", price=22000)
    roll = Product(restaurant=sushi, name="Roll California", description="10 piezas", price=28000)
    db.session.add_all([parrilla, sushi, vacio, hamburguesa, roll])
    db.session.commit()
    return {"parrilla": parrilla, "sushi": sushi, "vacio": vacio, "hamburguesa": hamburguesa, "roll": roll}


def _html(client, url):
    response = client.get(url)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_listado_muestra_los_restaurantes_existentes(client, catalogo):
    html = _html(client, "/restaurantes")

    assert "La Parrilla del Sur" in html
    assert "Sushi Galeras" in html
    assert "Carnes" in html
    assert "Ver menú" in html


def test_listado_esta_ordenado_por_nombre_sin_distinguir_mayusculas(client, app):
    db.session.add_all(
        [
            Restaurant(name="Zeta", cuisine="Rápida"),
            Restaurant(name="alfa", cuisine="Rápida"),
            Restaurant(name="Beta", cuisine="Rápida"),
        ]
    )
    db.session.commit()

    assert re.findall(r"<h2>(.*?)</h2>", _html(client, "/restaurantes")) == ["alfa", "Beta", "Zeta"]


def test_listado_sin_restaurantes_muestra_mensaje(client, app):
    assert "No se encontraron restaurantes" in _html(client, "/restaurantes")


def test_restaurante_muestra_solo_sus_productos(client, catalogo):
    html = _html(client, f"/restaurantes/{catalogo['sushi'].id}")

    assert "Roll California" in html
    assert "Hamburguesa clásica" not in html


def test_productos_muestran_nombre_descripcion_y_precio(client, catalogo):
    html = _html(client, f"/restaurantes/{catalogo['sushi'].id}")

    assert "Roll California" in html
    assert "10 piezas" in html
    assert "$ 28.000" in html


@pytest.mark.parametrize(
    "busqueda, esperado, descartado",
    [
        ("sushi", "Sushi Galeras", "La Parrilla del Sur"),
        ("PARRILLA", "La Parrilla del Sur", "Sushi Galeras"),
        ("japonesa", "Sushi Galeras", "La Parrilla del Sur"),
        ("CARNES", "La Parrilla del Sur", "Sushi Galeras"),
    ],
)
def test_busqueda_por_nombre_o_tipo_sin_distinguir_mayusculas(client, catalogo, busqueda, esperado, descartado):
    html = _html(client, f"/restaurantes?q={busqueda}")

    assert esperado in html
    assert descartado not in html


def test_busqueda_sin_coincidencias_muestra_mensaje(client, catalogo):
    html = _html(client, "/restaurantes?q=pizzeria")

    assert "No se encontraron restaurantes" in html
    assert "Sushi Galeras" not in html


@pytest.mark.parametrize("comodin", ["%25", "_", "%5C"])
def test_comodines_no_devuelven_todos_los_restaurantes(client, catalogo, comodin):
    html = _html(client, f"/restaurantes?q={comodin}")

    assert "No se encontraron restaurantes" in html
    assert "La Parrilla del Sur" not in html


@pytest.mark.parametrize(
    "busqueda, esperado, descartado",
    [("100%25", "Pizza 100%", "Pizza 1000"), ("a_b", "Cocina a_b", "Cocina axb")],
)
def test_comodines_se_buscan_como_texto(client, app, busqueda, esperado, descartado):
    db.session.add_all(
        Restaurant(name=name, cuisine="Rápida") for name in ("Pizza 100%", "Pizza 1000", "Cocina a_b", "Cocina axb")
    )
    db.session.commit()

    html = _html(client, f"/restaurantes?q={busqueda}")

    assert esperado in html
    assert descartado not in html


@pytest.mark.parametrize("busqueda", ["", "%20%20%20"])
def test_busqueda_vacia_muestra_todos(client, catalogo, busqueda):
    html = _html(client, f"/restaurantes?q={busqueda}")

    assert "La Parrilla del Sur" in html
    assert "Sushi Galeras" in html


def test_busqueda_se_recorta_a_la_longitud_maxima(client, catalogo):
    assert len(normalize_search("  " + "a" * 100)) == MAX_SEARCH_LENGTH
    assert normalize_search(None) == ""

    html = _html(client, "/restaurantes?q=" + "x" * 100)
    assert f'value="{"x" * MAX_SEARCH_LENGTH}"' in html
    assert "x" * (MAX_SEARCH_LENGTH + 1) not in html


def test_busqueda_escapa_html(client, catalogo):
    html = _html(client, "/restaurantes?q=<script>alert(1)</script>")

    assert "<script>alert(1)" not in html
    assert "&lt;script&gt;alert(1)" in html


def test_restaurante_sin_productos_muestra_estado_vacio(client, catalogo):
    html = _html(client, f"/restaurantes/{catalogo['vacio'].id}")

    assert "Este restaurante aún no tiene productos" in html
    assert "/carrito/agregar" not in html


@pytest.mark.parametrize("restaurant_id", ["9999", "0", str(2**31), "9" * 25])
def test_restaurante_inexistente_devuelve_404(client, catalogo, restaurant_id):
    assert client.get(f"/restaurantes/{restaurant_id}").status_code == 404


def test_menu_tiene_formulario_hacia_el_carrito(client, catalogo):
    html = _html(client, f"/restaurantes/{catalogo['sushi'].id}")
    form = re.search(r'<form[^>]*action="/carrito/agregar"[^>]*>(.*?)</form>', html, re.S)

    assert form is not None
    assert 'method="post"' in form.group(0)
    assert 'name="csrf_token"' in form.group(1)
    assert f'name="product_id" value="{catalogo["roll"].id}"' in form.group(1)
    assert 'name="quantity"' in form.group(1)
    assert 'min="1"' in form.group(1)
    assert 'max="20"' in form.group(1)


def test_imagenes_por_defecto_cuando_no_hay_imagen(client, catalogo):
    listado = _html(client, "/restaurantes")
    menu = _html(client, f"/restaurantes/{catalogo['sushi'].id}")

    assert 'src="/static/images/restaurante.svg"' in listado
    assert 'src="/static/images/producto.svg"' in menu


def test_imagen_propia_se_carga_desde_static(client, catalogo):
    catalogo["sushi"].image = "sushi.png"
    catalogo["roll"].image = "roll.png"
    db.session.commit()

    assert 'src="/static/images/sushi.png"' in _html(client, "/restaurantes")
    assert 'src="/static/images/roll.png"' in _html(client, f"/restaurantes/{catalogo['sushi'].id}")


@pytest.mark.parametrize("archivo", ["images/restaurante.svg", "images/producto.svg", "css/catalog.css", "js/catalog.js"])
def test_archivos_estaticos_del_catalogo_existen(client, archivo):
    response = client.get(f"/static/{archivo}")

    assert response.status_code == 200
    response.close()


def test_paginas_del_catalogo_cumplen_la_csp(client, catalogo):
    urls = [
        "/restaurantes",
        "/restaurantes?q=sin-resultados",
        f"/restaurantes/{catalogo['sushi'].id}",
        f"/restaurantes/{catalogo['vacio'].id}",
    ]
    for url in urls:
        html = _html(client, url)
        assert "style=" not in html
        assert "onclick=" not in html
        assert re.search(r"<script(?![^>]*\bsrc=)", html) is None
        assert re.search(r'<img[^>]*src="https?:', html) is None


def test_inicio_tiene_buscador_hacia_el_catalogo(client):
    html = _html(client, "/")
    form = re.search(r'<form[^>]*action="/restaurantes"[^>]*>(.*?)</form>', html, re.S)

    assert form is not None
    assert 'method="get"' in form.group(0)
    assert 'name="q"' in form.group(1)
