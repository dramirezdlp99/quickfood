"""Pruebas de registro e inicio de sesión (Ramirez · sección 9.3)."""

import pytest

from app.models import User
from app.services.auth_service import authenticate, validate_registration


@pytest.mark.parametrize(
    "campo_vacio", ["name", "email", "password", "confirm"],
)
def test_registro_rechaza_campos_obligatorios_vacios(client, campo_vacio):
    datos = {"name": "Ana", "email": "ana@test.com", "password": "Segura123*", "confirm": "Segura123*"}
    datos[campo_vacio] = ""
    response = client.post("/auth/registro", data=datos)
    assert response.status_code == 400
    assert "Todos los campos son obligatorios" in response.get_data(as_text=True)
    assert User.query.count() == 0


def test_registro_valido_crea_cliente_e_inicia_sesion(client):
    datos = {"name": "Ana", "email": "ANA@test.com", "password": "Segura123*", "confirm": "Segura123*"}
    response = client.post("/auth/registro", data=datos)
    assert response.status_code == 302
    user = User.query.filter_by(email="ana@test.com").one()
    assert user.role == "cliente"
    assert user.password_hash != "Segura123*"  # nunca se guarda en texto plano
    with client.session_transaction() as sess:
        assert sess["user_id"] == user.id


def test_registro_no_permite_elegir_rol_admin(client):
    datos = {"name": "Eve", "email": "eve@test.com", "password": "Segura123*", "confirm": "Segura123*", "role": "admin"}
    client.post("/auth/registro", data=datos)
    assert User.query.filter_by(email="eve@test.com").one().role == "cliente"


def test_registro_rechaza_correo_duplicado(client, make_user):
    make_user(email="ana@test.com")
    datos = {"name": "Ana", "email": "ana@test.com", "password": "Segura123*", "confirm": "Segura123*"}
    response = client.post("/auth/registro", data=datos)
    assert response.status_code == 400
    assert "Ya existe una cuenta" in response.get_data(as_text=True)


@pytest.mark.parametrize(
    "email, password, confirm, mensaje",
    [
        ("sin-arroba", "Segura123*", "Segura123*", "correo electrónico no es válido"),
        ("ana@test.com", "corta", "corta", "al menos 8 caracteres"),
        ("ana@test.com", "Segura123*", "Distinta123*", "no coinciden"),
    ],
)
def test_validacion_de_registro(app, email, password, confirm, mensaje):
    errores = validate_registration("Ana", email, password, confirm)
    assert any(mensaje in e for e in errores)


def test_login_acepta_credenciales_validas(client, make_user, login):
    make_user(email="ana@test.com")
    response = login("ana@test.com")
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" in sess


@pytest.mark.parametrize("email, password", [("ana@test.com", "Incorrecta1*"), ("nadie@test.com", "Prueba123*"), ("ana@test.com", "")])
def test_login_rechaza_credenciales_invalidas(client, make_user, login, email, password):
    make_user(email="ana@test.com")
    response = login(email, password)
    assert response.status_code == 401
    assert "Correo o contraseña incorrectos" in response.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_authenticate_ignora_mayusculas_en_correo(app, make_user):
    make_user(email="ana@test.com")
    assert authenticate("ANA@Test.com", "Prueba123*") is not None


def test_login_de_admin_redirige_al_panel(client, make_user, login):
    make_user(email="admin@test.com", role="admin")
    response = login("admin@test.com")
    assert response.headers["Location"].endswith("/admin/pedidos")


def test_login_no_redirige_a_sitios_externos(client, make_user):
    make_user(email="ana@test.com")
    response = client.post(
        "/auth/ingresar", data={"email": "ana@test.com", "password": "Prueba123*", "next": "https://sitio-malicioso.com"}
    )
    assert "sitio-malicioso" not in response.headers["Location"]


def test_logout_cierra_la_sesion(client, make_user, login):
    make_user(email="ana@test.com")
    login("ana@test.com")
    client.post("/auth/salir")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
