# QuickFood

Aplicación web de pedidos de comida (Flask + SQLite) construida para demostrar
un flujo **DevOps**: cada cambio pasa por pruebas automáticas y análisis de
calidad y seguridad **antes** de llegar a la rama principal.

Proyecto de la materia Pruebas y Mantenimiento de Software · Equipo: Mora · Daniers · Ramirez.

## Herramientas de calidad

| Herramienta | Qué detecta | Dónde se ejecuta |
|---|---|---|
| Pytest + pytest-cov | Funcionalidades que no cumplen lo esperado y % de código probado | Local y GitHub Actions (`pruebas`) |
| Bandit | Patrones inseguros en Python (secretos en el código, funciones peligrosas) | Local y GitHub Actions (`seguridad`) |
| pip-audit | Dependencias con vulnerabilidades conocidas | Local y GitHub Actions (`seguridad`) |
| SonarQube Cloud | Bugs, code smells, duplicación, hotspots de seguridad, cobertura | GitHub Actions (`sonarcloud`) |
| OWASP ZAP Baseline | Riesgos web en la app ejecutándose (cabeceras, cookies, etc.) | GitHub Actions (`zap`) contra una instancia temporal |

## Ejecutar en local (Windows · PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
flask --app run init-db
flask --app run seed-demo
flask --app run create-admin --email admin@quickfood.test --password "CambiaEsta2026*"
flask --app run run --debug
```

Abrir http://127.0.0.1:5000

## Verificaciones locales (las mismas del pipeline)

```powershell
python -m pytest
bandit -c bandit.yaml -r app
pip-audit -r requirements.txt
```

## Cómo agregar un módulo

* Crea `app/routes/<modulo>.py` con `bp = Blueprint("<modulo>", __name__, url_prefix="/...")`.
  Se registra solo (no hay que editar `app/__init__.py`).
* El menú superior muestra automáticamente estos enlaces cuando existen:
  `restaurants.index` (Mora), `cart.view` (Daniers), `admin.orders` (Ramirez).
* Para proteger una ruta: `from app.services.auth_service import login_required, admin_required`.
* Todo formulario `POST` debe incluir `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
* El JavaScript va en `app/static/js/` (la política CSP bloquea `<script>` en línea y `onclick=""`).
* Dinero en pesos enteros; en plantillas usa el filtro `{{ valor|cop }}` → `$ 12.500`.

## Flujo de ramas

`feature/*` → Pull Request → `develop` (1 aprobación + checks verdes) → Pull Request → `main` (2 aprobaciones + checks verdes).
Nadie hace push directo a `main` ni a `develop`.
