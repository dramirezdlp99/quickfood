# Registro de errores detectados antes de producción

Evidencia para la sustentación: cada fila es un problema que una herramienta
detectó **antes** de integrar el cambio, y cómo se corrigió.

| # | Fecha | Integrante | Herramienta | Qué detectó | Cómo se corrigió | PR |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

## Falsos positivos o hallazgos aceptados

| Herramienta | Hallazgo | Por qué no se corrige |
|---|---|---|
| SonarQube Cloud | Hotspot: CSRF desactivado en `TestingConfig` | Solo aplica a las pruebas automáticas; en la app real CSRF está activo |
| | | |
