"""Registro, inicio y cierre de sesión (módulo de Ramirez)."""

from urllib.parse import urlsplit

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from ..services.auth_service import (
    authenticate,
    load_current_user,
    log_in,
    register_user,
    validate_registration,
)

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def _load_user():
    load_current_user()


def _safe_next(target: str | None) -> str | None:
    """Solo permite redirigir a rutas internas (evita redirecciones abiertas)."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


@bp.route("/registro", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth/register.html", errors=[], form={})

    form = {key: request.form.get(key, "") for key in ("name", "email", "password", "confirm")}
    errors = validate_registration(form["name"], form["email"], form["password"], form["confirm"])
    if errors:
        return render_template("auth/register.html", errors=errors, form=form), 400

    user = register_user(form["name"], form["email"], form["password"])
    log_in(user)
    flash("¡Cuenta creada! Bienvenido a QuickFood.", "success")
    return redirect(url_for("home.index"))


@bp.route("/ingresar", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html", error=None, email="", next=request.args.get("next", ""))

    email = request.form.get("email", "")
    user = authenticate(email, request.form.get("password", ""))
    next_url = _safe_next(request.form.get("next"))
    if user is None:
        return render_template(
            "auth/login.html", error="Correo o contraseña incorrectos.", email=email, next=next_url or ""
        ), 401

    log_in(user)
    flash(f"Hola, {user.name}.", "success")
    if next_url:
        return redirect(next_url)
    return redirect(url_for("admin.orders") if user.is_admin else url_for("home.index"))


@bp.post("/salir")
def logout():
    session.clear()
    g.user = None
    flash("Sesión cerrada.", "info")
    return redirect(url_for("home.index"))
