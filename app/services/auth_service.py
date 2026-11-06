"""Reglas de usuarios: validación de registro, autenticación y control de acceso.

Otros módulos pueden proteger sus rutas así:

    from app.services.auth_service import login_required, admin_required

    @bp.post("/confirmar")
    @login_required
    def confirmar(): ...
"""

import re
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for

from ..extensions import db
from ..models import User

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")
MIN_PASSWORD_LENGTH = 8


def validate_registration(name: str, email: str, password: str, confirm: str) -> list[str]:
    """Devuelve la lista de errores; vacía si los datos son válidos."""
    errors = []
    name, email = (name or "").strip(), (email or "").strip().lower()

    if not name or not email or not password or not confirm:
        errors.append("Todos los campos son obligatorios.")
        return errors
    if len(name) > 80:
        errors.append("El nombre no puede superar 80 caracteres.")
    if not EMAIL_PATTERN.match(email):
        errors.append("El correo electrónico no es válido.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password != confirm:
        errors.append("Las contraseñas no coinciden.")
    if not errors and User.query.filter_by(email=email).first() is not None:
        errors.append("Ya existe una cuenta con ese correo.")
    return errors


def register_user(name: str, email: str, password: str) -> User:
    """Crea siempre un cliente: nadie puede registrarse como administrador."""
    user = User(name=name.strip(), email=email.strip().lower(), role="cliente")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(email: str, password: str) -> User | None:
    user = User.query.filter_by(email=(email or "").strip().lower()).first()
    if user is None or not password or not user.check_password(password):
        return None
    return user


def log_in(user: User) -> None:
    cart = session.get("cart")  # el carrito del visitante no debe perderse al iniciar sesión
    session.clear()  # evita reutilizar una sesión anterior (fijación de sesión)
    if cart:
        session["cart"] = cart
    session["user_id"] = user.id


def load_current_user() -> None:
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id is not None else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            flash("Debes iniciar sesión para continuar.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            flash("Debes iniciar sesión como administrador.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if not g.user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped
