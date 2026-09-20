document.addEventListener("DOMContentLoaded", function () {
  const botoesDesativar = document.querySelectorAll(".btn-desativar-produto");
  botoesDesativar.forEach(function (botao) {
    botao.addEventListener("click", function (evento) {
      const nome = botao.getAttribute("data-nome") || "este cupcake";
      const mensagem = "Desativar remove o cupcake da vitrine, mas ele continua no historico dos pedidos.\n\nDeseja confirmar a desativação?";
      if (!window.confirm(mensagem)) {
        evento.preventDefault();
      }
    });
  });
});
