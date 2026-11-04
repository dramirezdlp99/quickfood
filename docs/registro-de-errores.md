# Registro de errores detectados antes de producción

Evidencia para la sustentación: cada fila es un problema que una herramienta
detectó **antes** de integrar el cambio, y cómo se corrigió.

| # | Fecha | Integrante | Herramienta | Qué detectó | Cómo se corrigió | PR |
|---|---|---|---|---|---|---|
| 1 | 2026-11-02 | Ramirez | SonarQube Cloud | Expresión regular de validación de correo con backtracking super-lineal (riesgo de ReDoS) en `app/services/auth_service.py`, línea 20. El Quality Gate falló (Reliability C) aunque las pruebas pasaban | Regex sin ambigüedad: `^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$`; las pruebas siguen pasando | #1 |
| 2 | 2026-11-02 | Ramirez | SonarQube Cloud | `<th>` sin `scope` en el total de `app/templates/admin/order_detail.html`, línea 27 (accesibilidad WCAG 2 A) | "Total" como `<th scope="row">` y el valor como `<td>` | #1 |
| 3 | 2026-11-02 | Daniers | pytest-cov | `app/routes/cart.py` tenía 68 % de cobertura, por debajo del 80 % que exige SonarQube en código nuevo | Agregué pruebas de errores en actualizar/eliminar y quedó en 91 % (`5ba9be4`) | #2 |
| 4 | 2026-11-02 | Daniers | Revisión de código | Un `product_id` de 25 dígitos causaba `OverflowError` y respuesta 500 | Se agregó prueba y se limita a `2**31-1` (`26d6f37`) | #2 |
| 5 | 2026-11-02 | Daniers | Revisión de código | No existía prueba que verificara el rechazo de POST sin `csrf_token` | Se agregó (sin token → 400; con el token de la plantilla → aceptado) (`f688b3e`) | #2 |
| 6 | 2026-11-02 | Daniers | Revisión de código | El autoenvío del campo cantidad recargaba la página con cada tecla (WCAG 3.2.2) | Se quitó; el cambio se envía con Enter o con los botones − y + (`b18f6d7`) | #2 |
| 7 | 2026-11-02 | Daniers | Revisión de código (SonarQube S1192) | Mensajes y `"cart.view"` duplicados; el máximo 20 escrito a mano en mensajes y plantilla | Constantes construidas con `MAX_QUANTITY`, helper `_back_to_cart()` y `max_quantity` en la plantilla (`6ac8071`) | #2 |
| 8 | 2026-11-02 | Daniers | Revisión de código | `read()` escribía la sesión en cada GET; `update` no reconocía `" 0 "`/`"00"`; `add` consultaba la BD antes de validar y avisaba mal el límite de 20; ramas de validación sin probar | Se corrigió con pruebas primero; `cart_service.py` quedó en 100 % (`e0540c0`) | #2 |
| 9 | 2026-11-02 | Daniers | Revisión de código | Consulta N+1: la vista hacía una consulta por restaurante (4 consultas con 3 productos) | `selectinload(Product.restaurant)`: 2 consultas fijas; prueba que cuenta las consultas (`1315fef`) | #2 |
| 10 | 2026-11-02 | Daniers | Revisión de código (accesibilidad) | `aria-label` en `div` sin rol; botones desactivados al volver con "atrás"; bloque de enlace duplicado | `role="group"`, evento `pageshow` y URL calculada una vez, con pruebas (`62a9908`) | #2 |
| 11 | 2026-11-03 | Ramirez | Pytest | Demo intencional: se quitó `@admin_required` de `/admin/pedidos`; fallaron 2 pruebas de seguridad (un usuario sin sesión y un cliente podían entrar) | Se restauró el decorador; las 106 pruebas pasan | #3 |
| 12 | 2026-11-03 | Ramirez | Bandit (B105) | Demo intencional: clave secreta escrita en `app/config.py`, línea 15. Las pruebas, SonarQube y ZAP pasaron; solo Bandit lo detectó | Se volvió a leer de `QUICKFOOD_SECRET_KEY` o se genera aleatoria | #3 |
| 13 | 2026-11-03 | Ramirez | pip-audit | Demo intencional: `requests==2.31.0` con vulnerabilidades conocidas (PYSEC-2026-1872, -1873, -2275) | Actualizado a `requests==2.34.2` | #3 |
| 14 | 2026-11-03 | Ramirez | OWASP ZAP Baseline | 2 alertas Medium (CSP con comodín en img-src y style-src 'unsafe-inline') y 2 Low (faltaban Cross-Origin-Embedder-Policy y Cross-Origin-Resource-Policy) | CSP sin comodín ni unsafe-inline; cabeceras COEP require-corp y CORP same-origin; prueba nueva en tests/unit/test_app.py | #4 |
| 15 | 2026-11-04 | Mora | Pytest | Al integrar el catálogo fallaron 2 casos de `test_enlace_seguir_comprando_lleva_al_inicio_sin_modulo_de_restaurantes` en `tests/unit/test_cart.py`: esperaban `href="/"` porque suponían que el módulo de restaurantes no existía | La plantilla del carrito ya enlaza bien a `/restaurantes`; se ajustó solo esa prueba para esperar el nuevo enlace y se renombró a `test_enlace_seguir_comprando_lleva_al_catalogo` | pendiente |

## Falsos positivos o hallazgos aceptados

| Herramienta | Hallazgo | Por qué no se corrige |
|---|---|---|
| Consola del navegador (CSP) | La CSP bloquea los `.map` de Bootstrap desde `cdn.jsdelivr.net` | Solo ocurre con DevTools abierto y no afecta al usuario |
| OWASP ZAP (Low) | Server Leaks Version Information: el servidor de desarrollo envía "Werkzeug/x Python/y" | La cabecera la pone el servidor de desarrollo de Flask, no la app; en producción se usaría gunicorn o nginx sin esa cabecera |
| OWASP ZAP (10 Informational) | Login detectado, cookie de sesión firmada (Base64), cabeceras Sec-Fetch ausentes en las peticiones de ZAP, contenido cacheable | Son observaciones informativas, no vulnerabilidades |