document.addEventListener("DOMContentLoaded", function () {
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) {
      return meta.content;
    }
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) {
      return input.value;
    }
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function atualizarBadge(total) {
    const badge = document.getElementById("badge-carrinho");
    if (!badge) return;
    const num = parseInt(total, 10) || 0;
    badge.textContent = num;
    if (num > 0) {
      badge.style.display = "inline-flex";
    } else {
      badge.style.display = "none";
    }
  }

  function exibirSnackbar(mensagem, tipo) {
    tipo = tipo || "sucesso";
    var container = document.getElementById("snackbar-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "snackbar-container";
      container.className = "snackbar-container";
      document.body.appendChild(container);
    }

    var snackbar = document.createElement("div");
    snackbar.className = "snackbar snackbar-" + tipo;
    snackbar.textContent = mensagem;
    container.appendChild(snackbar);

    setTimeout(function () {
      snackbar.classList.add("fade-out");
      setTimeout(function () {
        if (snackbar.parentNode) {
          snackbar.parentNode.removeChild(snackbar);
        }
      }, 300);
    }, 3000);
  }

  window.getCsrfToken = getCsrfToken;
  window.exibirSnackbar = exibirSnackbar;

  // Intercepta formulário de adicionar ao carrinho na tela de detalhe
  var formAdicionar = document.getElementById("form-adicionar-carrinho") || document.querySelector(".formulario-carrinho");
  if (formAdicionar) {
    formAdicionar.addEventListener("submit", function (evento) {
      evento.preventDefault();
      var btn = formAdicionar.querySelector("button[type=submit]");
      if (btn) btn.disabled = true;

      var formData = new FormData(formAdicionar);
      var url = formAdicionar.action || "/carrinho/adicionar/";

      fetch(url, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
      })
        .then(function (resposta) {
          if (resposta.redirected) {
            window.location.href = resposta.url;
            return null;
          }
          return resposta.json().then(function (dados) {
            return { status: resposta.status, dados: dados };
          });
        })
        .then(function (resultado) {
          if (btn) btn.disabled = false;
          if (!resultado) return;

          var status = resultado.status;
          var dados = resultado.dados;

          if (status === 401 && dados.redirecionar) {
            window.location.href = dados.redirecionar;
            return;
          }

          if (status === 200 && dados.sucesso) {
            atualizarBadge(dados.quantidade_total);
            exibirSnackbar(dados.mensagem || "Cupcake adicionado ao carrinho!");
          } else {
            exibirSnackbar(dados.erro || "Não foi possível adicionar ao carrinho.", "erro");
          }
        })
        .catch(function () {
          if (btn) btn.disabled = false;
          exibirSnackbar("Erro de comunicação com o servidor.", "erro");
        });
    });
  }

  // Interações na tela do carrinho (/carrinho/)
  function atualizarTelaCarrinho(dados) {
    var resumoQtd = document.getElementById("resumo-quantidade-total");
    var resumoTotal = document.getElementById("resumo-total-geral");
    var vazioCard = document.getElementById("carrinho-vazio");
    var conteudoCard = document.getElementById("carrinho-conteudo");

    if (resumoQtd) resumoQtd.textContent = dados.quantidade_total;
    if (resumoTotal) resumoTotal.textContent = dados.total_geral_formatado;
    atualizarBadge(dados.quantidade_total);

    if (dados.quantidade_total === 0) {
      if (conteudoCard) conteudoCard.style.display = "none";
      if (vazioCard) vazioCard.style.display = "block";
    }

    document.dispatchEvent(new CustomEvent("carrinho:atualizado", { detail: dados }));
  }

  // Alteração de quantidade (+ / -)
  document.querySelectorAll(".btn-alterar-qtd").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var card = botao.closest(".item-carrinho-card");
      if (!card) return;
      var produtoId = card.getAttribute("data-produto-id");
      var input = card.querySelector(".input-quantidade");
      var subtotalEl = document.getElementById("subtotal-produto-hidden-" + produtoId) || card.querySelector(".valor-subtotal");
      var qtdAtual = parseInt(input.value || "1", 10);
      var acao = botao.getAttribute("data-acao");
      var novaQtd = acao === "aumentar" ? qtdAtual + 1 : qtdAtual - 1;

      var formData = new FormData();
      formData.append("produto_id", produtoId);
      formData.append("quantidade", novaQtd);

      fetch("/carrinho/alterar/", {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
      })
        .then(function (resposta) {
          if (resposta.redirected) {
            window.location.href = resposta.url;
            return null;
          }
          return resposta.json().then(function (dados) {
            return { status: resposta.status, dados: dados };
          });
        })
        .then(function (resultado) {
          if (!resultado) return;
          var status = resultado.status;
          var dados = resultado.dados;

          if (status === 200 && dados.sucesso) {
            if (dados.removido || dados.quantidade === 0) {
              card.remove();
            } else {
              input.value = dados.quantidade;
              if (subtotalEl) subtotalEl.textContent = dados.subtotal_item_formatado;
            }
            atualizarTelaCarrinho(dados);
          } else {
            exibirSnackbar(dados.erro || "Não foi possível alterar a quantidade.", "erro");
          }
        })
        .catch(function () {
          exibirSnackbar("Erro de comunicação com o servidor.", "erro");
        });
    });
  });

  // Remoção de item
  document.querySelectorAll(".btn-remover-item").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var produtoId = botao.getAttribute("data-produto-id");
      var card = document.getElementById("item-carrinho-" + produtoId) || botao.closest(".item-carrinho-card");

      var formData = new FormData();
      formData.append("produto_id", produtoId);

      fetch("/carrinho/remover/", {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
      })
        .then(function (resposta) {
          if (resposta.redirected) {
            window.location.href = resposta.url;
            return null;
          }
          return resposta.json().then(function (dados) {
            return { status: resposta.status, dados: dados };
          });
        })
        .then(function (resultado) {
          if (!resultado) return;
          var status = resultado.status;
          var dados = resultado.dados;

          if (status === 200 && dados.sucesso) {
            if (card) card.remove();
            atualizarTelaCarrinho(dados);
            exibirSnackbar("Item removido do carrinho.");
          } else {
            exibirSnackbar(dados.erro || "Não foi possível remover o item.", "erro");
          }
        })
        .catch(function () {
          exibirSnackbar("Erro de comunicação com o servidor.", "erro");
        });
    });
  });
});
