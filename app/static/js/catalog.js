"use strict";

// Evita agregar el producto dos veces por un doble clic en "Agregar".
document.addEventListener("submit", (event) => {
  if (event.target.matches(".js-add-to-cart")) {
    event.target.querySelector("button[type='submit']").disabled = true;
  }
});

// Al volver con "atrás" el navegador restaura la página desde su caché con los botones desactivados.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    document.querySelectorAll(".js-add-to-cart button[type='submit']").forEach((button) => {
      button.disabled = false;
    });
  }
});
