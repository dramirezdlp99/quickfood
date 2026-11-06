"use strict";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("#cart-page form, #orders-page form").forEach((form) => {
    form.addEventListener("submit", () => {
      form.querySelectorAll("button[type='submit']").forEach((button) => {
        button.disabled = true;
        button.dataset.busy = "true";
      });
    });
  });
});

// Al volver con "atrás" el navegador restaura la página desde su caché con los botones desactivados.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    document.querySelectorAll("#cart-page button[data-busy], #orders-page button[data-busy]").forEach((button) => {
      button.disabled = false;
      delete button.dataset.busy;
    });
  }
});
