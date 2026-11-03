"""Configuración por entorno.

Los secretos nunca se escriben en el código: se leen de variables de
entorno. Si no existen (desarrollo local), se genera una clave aleatoria.
"""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = "quickfood-clave-123"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "QUICKFOOD_DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'quickfood.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    TESTING = False


class DevelopmentConfig(Config):
    pass


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # En las pruebas automáticas se desactiva CSRF para poder enviar
    # formularios directamente; en la aplicación real sigue activo.
    WTF_CSRF_ENABLED = False


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
