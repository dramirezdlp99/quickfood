"use strict";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".js-quantity-input").forEach((input) => {
    input.addEventListener("change", () => {
      if (input.form && input.reportValidity()) {
        input.form.requestSubmit();
      }
    });
  });

  document.querySelectorAll("#cart-page form").forEach((form) => {
    form.addEventListener("submit", () => {
      form.querySelectorAll("button[type='submit']").forEach((button) => {
        button.disabled = true;
      });
    });
  });
});
