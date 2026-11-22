/*
 * Przełącznik motywu jasny / ciemny.
 * Wybór zapisywany w localStorage (tylko ta przeglądarka); bez wyboru – motyw systemowy.
 * Wczesne ustawienie motywu (bez „mignięcia” jasnej strony) robi skrypt inline w <head>.
 */
(function () {
  "use strict";
  var KLUCZ = "krag-motyw";

  function zapisz(motyw) {
    try { localStorage.setItem(KLUCZ, motyw); } catch (e) { /* tryb prywatny itp. */ }
  }

  function ustaw(motyw) {
    document.documentElement.setAttribute("data-bs-theme", motyw);
    document.querySelectorAll(".przelacznik-motywu").forEach(function (przycisk) {
      var ciemny = motyw === "dark";
      var opis = ciemny ? "Włącz jasny motyw" : "Włącz ciemny motyw";
      przycisk.setAttribute("aria-pressed", ciemny ? "true" : "false");
      przycisk.setAttribute("title", opis);
      przycisk.setAttribute("aria-label", opis);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    ustaw(document.documentElement.getAttribute("data-bs-theme") || "light");
    document.querySelectorAll(".przelacznik-motywu").forEach(function (przycisk) {
      przycisk.addEventListener("click", function () {
        var nowy = document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
        zapisz(nowy);
        ustaw(nowy);
      });
    });
  });

  // Zmiana motywu w systemie – tylko gdy użytkownik sam niczego nie wybrał.
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
      var wybrany = null;
      try { wybrany = localStorage.getItem(KLUCZ); } catch (err) { /* brak dostępu */ }
      if (!wybrany) { ustaw(e.matches ? "dark" : "light"); }
    });
  }
})();
