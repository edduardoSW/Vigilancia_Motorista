// Aplica o tema salvo antes de desenhar a tela (carregado de forma síncrona no <head>, sem script inline).
(function () {
  var theme = "noite";
  try {
    theme = localStorage.getItem("drivesafe-tema") || "noite";
  } catch (error) {
    // navegador sem armazenamento local: fica no tema da noite
  }
  document.documentElement.setAttribute("data-theme", theme === "dia" ? "light" : "dark");
})();
