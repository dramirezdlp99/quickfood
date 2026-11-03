"""Pruebas de la base del proyecto (fábrica, inicio, errores y cabeceras)."""

from app import create_app


def test_app_se_crea_en_modo_pruebas(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_cada_app_tiene_clave_secreta_aleatoria():
    assert create_app("testing").config["SECRET_KEY"]


def test_inicio_responde_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "QuickFood" in response.get_data(as_text=True)


def test_ruta_inexistente_devuelve_404(client):
    response = client.get("/esta-ruta-no-existe")
    assert response.status_code == 404
    assert "no existe" in response.get_data(as_text=True)


def test_respuestas_incluyen_cabeceras_de_seguridad(client):
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"

def test_cabeceras_corregidas_por_reporte_zap(client):
    headers = client.get("/").headers
    csp = headers["Content-Security-Policy"]
    assert "unsafe-inline" not in csp
    assert "https:;" not in csp
    assert headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert headers["Cross-Origin-Embedder-Policy"] == "require-corp"


def test_filtro_cop_formatea_pesos(app):
    assert app.jinja_env.filters["cop"](12500) == "$ 12.500"
    assert app.jinja_env.filters["cop"](None) == "$ 0"
