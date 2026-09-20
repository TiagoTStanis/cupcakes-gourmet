document.addEventListener("DOMContentLoaded", function () {
  const campos = document.getElementById("dados-cartao");
  const formas = document.querySelectorAll('input[name="forma_pagamento"]');
  const revisao = document.getElementById("revisao-pagamento");
  let revisando = false;
  function mostrarRevisao() {
    if (!revisao) return;
    const selecionada = document.querySelector('input[name="forma_pagamento"]:checked');
    const cartao = selecionada.value === "CARTAO";
    revisando = true;
    revisao.hidden = false;
    campos.hidden = true;
    document.querySelector(".checkout-opcoes").hidden = true;
    const parcelas = document.getElementById("cartao-parcelas");
    document.getElementById("revisao-forma").textContent = cartao
      ? "Cartão final " + document.getElementById("cartao-numero").value.replace(/\D/g, "").slice(-4) + ": " + parcelas.selectedOptions[0].textContent
      : "PIX simulado: validade de 30 minutos após confirmar o pedido.";
    document.getElementById("pagamento-avancar").textContent = "Confirmar pedido";
    document.getElementById("pagamento-titulo").textContent = "Revise seu pedido";
    document.querySelectorAll(".checkout-progresso li").forEach(function (etapa, indice) {
      etapa.removeAttribute("aria-current");
      if (indice === 2) etapa.setAttribute("aria-current", "step");
    });
    document.getElementById("pagamento-titulo").focus();
  }
  if (campos) {
    function escolherForma() {
      const selecionada = document.querySelector('input[name="forma_pagamento"]:checked');
      const cartao = !formas.length || (selecionada && selecionada.value === "CARTAO");
      campos.hidden = !cartao;
      campos.disabled = !cartao;
    }
    formas.forEach(function (campo) { campo.addEventListener("change", escolherForma); });
    escolherForma();
    if (revisao) {
      document.getElementById("pagamento-avancar").textContent = "Revisar pedido";
      document.getElementById("pagamento-voltar").addEventListener("click", function () {
        revisando = false;
        revisao.hidden = true;
        document.querySelector(".checkout-opcoes").hidden = false;
        escolherForma();
        document.getElementById("pagamento-avancar").textContent = "Revisar pedido";
        document.getElementById("pagamento-titulo").textContent = "Forma de pagamento";
        document.querySelectorAll(".checkout-progresso li").forEach(function (etapa, indice) {
          etapa.removeAttribute("aria-current");
          if (indice === 1) etapa.setAttribute("aria-current", "step");
        });
        document.getElementById("pagamento-titulo").focus();
      });
    }
    const numero = document.getElementById("cartao-numero");
    numero.addEventListener("input", function () {
      const digitos = numero.value.replace(/\D/g, "").slice(0, 19);
      numero.value = digitos.replace(/(.{4})/g, "$1 ").trim();
      numero.setCustomValidity("");
    });
    const validade = document.getElementById("cartao-validade");
    validade.addEventListener("input", function () {
      const digitos = validade.value.replace(/\D/g, "").slice(0, 4);
      validade.value = digitos.length > 2 ? digitos.slice(0, 2) + "/" + digitos.slice(2) : digitos;
    });
    const cvv = document.getElementById("cartao-cvv");
    cvv.addEventListener("input", function () { cvv.value = cvv.value.replace(/\D/g, "").slice(0, 3); });
    document.getElementById("formulario-pagamento").addEventListener("submit", function (evento) {
      if (campos.disabled) {
        if (revisao && !revisando) {
          evento.preventDefault();
          mostrarRevisao();
        }
        return;
      }
      const digitos = numero.value.replace(/\D/g, "");
      let soma = 0;
      Array.from(digitos).reverse().forEach(function (caractere, indice) {
        let digito = Number(caractere);
        if (indice % 2) digito *= 2;
        soma += digito > 9 ? digito - 9 : digito;
      });
      if (digitos.length < 13 || new Set(digitos).size === 1 || soma % 10 !== 0) {
        evento.preventDefault();
        numero.setCustomValidity("Informe um número de cartão válido.");
        numero.reportValidity();
        return;
      }
      if (revisao && !revisando) {
        evento.preventDefault();
        mostrarRevisao();
      }
    });
  }

  const contador = document.getElementById("pix-contador");
  if (contador) {
    const expiraEm = new Date(contador.dataset.expiraEm).getTime();
    function atualizarContador() {
      const segundos = Math.max(0, Math.ceil((expiraEm - Date.now()) / 1000));
      contador.textContent = String(Math.floor(segundos / 60)).padStart(2, "0") + ":" + String(segundos % 60).padStart(2, "0");
      if (!segundos) {
        document.getElementById("pix-confirmar").disabled = true;
        window.location.reload();
      }
    }
    atualizarContador();
    window.setInterval(atualizarContador, 1000);
  }

  const copiar = document.getElementById("pix-copiar");
  if (copiar) copiar.addEventListener("click", async function () {
    const codigo = document.getElementById("pix-codigo");
    const feedback = document.getElementById("pix-feedback");
    try {
      if (!navigator.clipboard) throw new Error("Cópia automática indisponível");
      await navigator.clipboard.writeText(codigo.value);
      feedback.textContent = "Código copiado.";
    } catch (erro) {
      codigo.focus();
      codigo.select();
      feedback.textContent = "Selecione e copie o código acima.";
    }
  });
});
