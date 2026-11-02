"use strict";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("#cart-page form").forEach((form) => {
    form.addEventListener("submit", () => {
      form.querySelectorAll("button[type='submit']").forEach((button) => {
        button.disabled = true;
      });
    });
  });
});
