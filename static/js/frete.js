document.addEventListener("DOMContentLoaded", function () {
  function obterCsrf() {
    if (typeof window.getCsrfToken === "function") {
      return window.getCsrfToken();
    }
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function mostrarNotificacao(mensagem, tipo) {
    if (typeof window.exibirSnackbar === "function") {
      window.exibirSnackbar(mensagem, tipo);
    }
  }

  var inputCep = document.getElementById("input-cep");
  var btnCalcularFrete = document.getElementById("btn-calcular-frete");
  var feedbackFrete = document.getElementById("feedback-frete");

  var inputCupom = document.getElementById("input-cupom");
  var btnAplicarCupom = document.getElementById("btn-aplicar-cupom");
  var feedbackCupom = document.getElementById("feedback-cupom");

  var resumoSubtotal = document.getElementById("resumo-subtotal");
  var linhaDesconto = document.getElementById("linha-desconto");
  var resumoDesconto = document.getElementById("resumo-desconto");
  var resumoFrete = document.getElementById("resumo-frete");
  var resumoTotalGeral = document.getElementById("resumo-total-geral");

  // Máscara para o campo de CEP (00000-000)
  if (inputCep) {
    inputCep.addEventListener("input", function () {
      var valor = inputCep.value.replace(/\D/g, "").slice(0, 8);
      if (valor.length > 5) {
        inputCep.value = valor.slice(0, 5) + "-" + valor.slice(5);
      } else {
        inputCep.value = valor;
      }
    });

    inputCep.addEventListener("keypress", function (evento) {
      if (evento.key === "Enter") {
        evento.preventDefault();
        calcularFrete();
      }
    });
  }

  if (inputCupom) {
    inputCupom.addEventListener("keypress", function (evento) {
      if (evento.key === "Enter") {
        evento.preventDefault();
        aplicarCupom();
      }
    });
  }

  function atualizarResumoUI(resumo) {
    if (!resumo) return;

    if (resumoSubtotal) {
      resumoSubtotal.textContent = resumo.subtotal_formatado;
    }

    var valorDescontoNum = parseFloat(resumo.desconto) || 0;
    if (linhaDesconto && resumoDesconto) {
      if (valorDescontoNum > 0) {
        linhaDesconto.style.display = "flex";
        resumoDesconto.textContent = "- " + resumo.desconto_formatado;
      } else {
        linhaDesconto.style.display = "none";
        resumoDesconto.textContent = "- R$ 0,00";
      }
    }

    if (resumoFrete) {
      if (resumo.frete_gratis) {
        resumoFrete.innerHTML = '<span class="tag-frete-gratis">Frete Grátis</span>';
      } else if (resumo.uf) {
        resumoFrete.textContent = resumo.frete_formatado;
      } else {
        resumoFrete.textContent = "Calcule acima";
      }
    }

    if (resumoTotalGeral) {
      resumoTotalGeral.textContent = resumo.total_formatado;
    }

    // Se houver cupom ativo na sessão, exibe o feedback
    if (resumo.cupom_codigo && feedbackCupom) {
      feedbackCupom.style.display = "block";
      feedbackCupom.className = "feedback-info feedback-sucesso";
      feedbackCupom.innerHTML =
        '<div class="cupom-ativo-linha">' +
        '<span>Cupom <strong>' + resumo.cupom_codigo + '</strong> aplicado (' + resumo.desconto_formatado + ')</span>' +
        '<button type="button" id="btn-remover-cupom" class="btn-remover-cupom" title="Remover cupom">Remover</button>' +
        '</div>';
      vincularBotaoRemoverCupom();
    } else if (!resumo.cupom_codigo && feedbackCupom && !feedbackCupom.classList.contains("feedback-erro")) {
      feedbackCupom.style.display = "none";
      feedbackCupom.innerHTML = "";
    }
  }

  function calcularFrete() {
    if (!inputCep) return;
    var cep = inputCep.value.trim();

    if (!cep) {
      mostrarNotificacao("Informe o CEP para calcular o frete.", "erro");
      if (feedbackFrete) {
        feedbackFrete.style.display = "block";
        feedbackFrete.className = "feedback-info feedback-erro";
        feedbackFrete.textContent = "Informe o CEP para cálculo.";
      }
      return;
    }

    if (btnCalcularFrete) btnCalcularFrete.disabled = true;

    fetch("/pedidos/cep/consultar/", {
      method: "POST",
      body: JSON.stringify({ cep: cep }),
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": obterCsrf(),
      },
    })
      .then(function (resposta) {
        return resposta.json().then(function (dados) {
          return { status: resposta.status, dados: dados };
        });
      })
      .then(function (resultado) {
        if (btnCalcularFrete) btnCalcularFrete.disabled = false;
        var dados = resultado.dados;

        if (resultado.status === 200 && dados.sucesso) {
          if (feedbackFrete) {
            feedbackFrete.style.display = "block";
            feedbackFrete.className = "feedback-info feedback-sucesso";
            var textoFrete = dados.frete.gratis
              ? "Frete grátis (" + dados.frete.prazo_dias + " dias úteis)"
              : dados.frete.valor_formatado + " (prazo de " + dados.frete.prazo_dias + " dias úteis)";
            feedbackFrete.innerHTML =
              "<strong>Entrega para " + dados.endereco.cidade + "/" + dados.endereco.uf + ":</strong> " + textoFrete;
          }
          atualizarResumoUI(dados.resumo);
          mostrarNotificacao("Frete calculado com sucesso!");
        } else {
          var erroMsg = dados.erro || "Não foi possível calcular o frete.";
          if (feedbackFrete) {
            feedbackFrete.style.display = "block";
            feedbackFrete.className = "feedback-info feedback-erro";
            feedbackFrete.textContent = erroMsg;
          }
          mostrarNotificacao(erroMsg, "erro");
        }
      })
      .catch(function () {
        if (btnCalcularFrete) btnCalcularFrete.disabled = false;
        mostrarNotificacao("Erro de comunicação ao calcular frete.", "erro");
      });
  }

  function aplicarCupom() {
    if (!inputCupom) return;
    var codigo = inputCupom.value.trim();

    if (!codigo) {
      mostrarNotificacao("Digite o código do cupom.", "erro");
      return;
    }

    if (btnAplicarCupom) btnAplicarCupom.disabled = true;

    fetch("/pedidos/cupom/aplicar/", {
      method: "POST",
      body: JSON.stringify({ codigo: codigo }),
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": obterCsrf(),
      },
    })
      .then(function (resposta) {
        return resposta.json().then(function (dados) {
          return { status: resposta.status, dados: dados };
        });
      })
      .then(function (resultado) {
        if (btnAplicarCupom) btnAplicarCupom.disabled = false;
        var dados = resultado.dados;

        if (resultado.status === 200 && dados.sucesso) {
          inputCupom.value = "";
          atualizarResumoUI(dados.resumo);
          mostrarNotificacao(dados.mensagem || "Cupom aplicado com sucesso!");
        } else {
          var erroMsg = dados.erro || "Cupom inválido.";
          if (feedbackCupom) {
            feedbackCupom.style.display = "block";
            feedbackCupom.className = "feedback-info feedback-erro";
            feedbackCupom.textContent = erroMsg;
          }
          mostrarNotificacao(erroMsg, "erro");
        }
      })
      .catch(function () {
        if (btnAplicarCupom) btnAplicarCupom.disabled = false;
        mostrarNotificacao("Erro de comunicação ao aplicar cupom.", "erro");
      });
  }

  function removerCupom() {
    fetch("/pedidos/cupom/remover/", {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": obterCsrf(),
      },
    })
      .then(function (resposta) {
        return resposta.json().then(function (dados) {
          return { status: resposta.status, dados: dados };
        });
      })
      .then(function (resultado) {
        var dados = resultado.dados;
        if (resultado.status === 200 && dados.sucesso) {
          if (feedbackCupom) {
            feedbackCupom.style.display = "none";
            feedbackCupom.innerHTML = "";
            feedbackCupom.className = "feedback-info";
          }
          if (inputCupom) inputCupom.value = "";
          atualizarResumoUI(dados.resumo);
          mostrarNotificacao("Cupom removido.");
        }
      })
      .catch(function () {
        mostrarNotificacao("Erro de comunicação ao remover cupom.", "erro");
      });
  }

  function vincularBotaoRemoverCupom() {
    var btnRemover = document.getElementById("btn-remover-cupom");
    if (btnRemover) {
      btnRemover.addEventListener("click", function () {
        removerCupom();
      });
    }
  }

  function reconsultarResumo() {
    fetch("/pedidos/resumo/", {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then(function (resposta) {
        if (resposta.ok) {
          return resposta.json();
        }
        return null;
      })
      .then(function (dados) {
        if (dados && dados.sucesso && dados.resumo) {
          if (dados.resumo.cep && inputCep && !inputCep.value) {
            inputCep.value = dados.resumo.cep;
          }
          atualizarResumoUI(dados.resumo);
        }
      })
      .catch(function () {
        // Silencioso se o usuário ainda não tiver itens
      });
  }

  if (btnCalcularFrete) {
    btnCalcularFrete.addEventListener("click", calcularFrete);
  }

  if (btnAplicarCupom) {
    btnAplicarCupom.addEventListener("click", aplicarCupom);
  }

  // Atualiza resumo financeiro quando o carrinho for alterado (+, - ou remoção de itens)
  document.addEventListener("carrinho:atualizado", function () {
    reconsultarResumo();
  });

  // Consulta estado inicial salvo na sessão
  reconsultarResumo();
});
