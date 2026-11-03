"""Fábrica de la aplicación QuickFood.

Los blueprints se registran automáticamente: cualquier archivo dentro de
``app/routes`` que defina una variable ``bp`` (un ``Blueprint``) queda
registrado sin tocar este archivo. Así cada integrante agrega su módulo
sin generar conflictos de Git en este punto común.
"""

import importlib
import os
import pkgutil

from flask import Flask, Blueprint, g, render_template

from .config import CONFIGS
from .extensions import csrf, db


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIGS[config_name])
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    # Importa los modelos para que SQLAlchemy conozca todas las tablas.
    from . import models  # noqa: F401

    _register_blueprints(app)
    _register_helpers(app)
    _register_error_pages(app)
    _register_security_headers(app)

    from .cli import register_cli

    register_cli(app)
    return app


def _register_blueprints(app: Flask) -> None:
    from . import routes

    for module_info in pkgutil.iter_modules(routes.__path__):
        module = importlib.import_module(f"{routes.__name__}.{module_info.name}")
        blueprint = getattr(module, "bp", None)
        if isinstance(blueprint, Blueprint):
            app.register_blueprint(blueprint)


def _register_helpers(app: Flask) -> None:
    @app.template_filter("cop")
    def format_cop(value) -> str:
        """Formatea un entero como pesos colombianos: 12500 -> $ 12.500"""
        return "$ " + f"{int(value or 0):,}".replace(",", ".")

    @app.context_processor
    def inject_helpers():
        def endpoint_exists(name: str) -> bool:
            return name in app.view_functions

        return {"endpoint_exists": endpoint_exists, "current_user": g.get("user")}


def _register_error_pages(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(_error):
        return render_template("errors/error.html", code=400, message="Solicitud no válida."), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/error.html", code=403, message="No tienes permiso para ver esta página."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/error.html", code=404, message="La página que buscas no existe."), 404


def _register_security_headers(app: Flask) -> None:
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )

    @app.after_request
    def add_headers(response):
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Embedder-Policy", "require-corp")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response
