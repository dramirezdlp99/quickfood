# Registro de errores detectados antes de producción

Evidencia para la sustentación: cada fila es un problema que una herramienta
detectó **antes** de integrar el cambio, y cómo se corrigió.

| # | Fecha | Integrante | Herramienta | Qué detectó | Cómo se corrigió | PR |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | 2026-11-02 | Daniers | pytest-cov | `app/routes/cart.py` tenía 68 % de cobertura, por debajo del 80 % que exige SonarQube en código nuevo | Agregué pruebas de errores en actualizar/eliminar y quedó en 91 % (`5ba9be4`) | #pendiente |
| 5 | 2026-11-02 | Daniers | Revisión de código | Un `product_id` de 25 dígitos causaba `OverflowError` y respuesta 500 | Se agregó prueba y se limita a `2**31-1` (`26d6f37`) | #pendiente |
| 6 | 2026-11-02 | Daniers | Revisión de código | No existía prueba que verificara el rechazo de POST sin `csrf_token` | Se agregó (sin token → 400; con el token de la plantilla → aceptado) (`f688b3e`) | #pendiente |
| 7 | 2026-11-02 | Daniers | Revisión de código | El autoenvío del campo cantidad recargaba la página con cada tecla (WCAG 3.2.2) | Se quitó; el cambio se envía con Enter o con los botones − y + (`b18f6d7`) | #pendiente |
| 8 | 2026-11-02 | Daniers | Revisión de código (SonarQube S1192) | Mensajes y `"cart.view"` duplicados; el máximo 20 escrito a mano en mensajes y plantilla | Constantes construidas con `MAX_QUANTITY`, helper `_back_to_cart()` y `max_quantity` en la plantilla (`6ac8071`) | #pendiente |
| 9 | 2026-11-02 | Daniers | Revisión de código | `read()` escribía la sesión en cada GET; `update` no reconocía `" 0 "`/`"00"`; `add` consultaba la BD antes de validar y avisaba mal el límite de 20; ramas de validación sin probar | Se corrigió con pruebas primero; `cart_service.py` quedó en 100 % (`e0540c0`) | #pendiente |
| 10 | 2026-11-02 | Daniers | Revisión de código | Consulta N+1: la vista hacía una consulta por restaurante (4 consultas con 3 productos) | `selectinload(Product.restaurant)`: 2 consultas fijas; prueba que cuenta las consultas (`1315fef`) | #pendiente |
| 11 | 2026-11-02 | Daniers | Revisión de código (accesibilidad) | `aria-label` en `div` sin rol; botones desactivados al volver con "atrás"; bloque de enlace duplicado | `role="group"`, evento `pageshow` y URL calculada una vez, con pruebas (`62a9908`) | #pendiente |

## Falsos positivos o hallazgos aceptados

| Herramienta | Hallazgo | Por qué no se corrige |
|---|---|---|
| SonarQube Cloud | Hotspot: CSRF desactivado en `TestingConfig` | Solo aplica a las pruebas automáticas; en la app real CSRF está activo |
| | | |
| Consola del navegador (CSP) | La CSP bloquea los `.map` de Bootstrap desde `cdn.jsdelivr.net` | Solo ocurre con DevTools abierto y no afecta al usuario |
