document.addEventListener("DOMContentLoaded", function () {
  const contador = document.getElementById("checkout-contador");
  if (contador) {
    const expiraEm = new Date(contador.dataset.expiraEm).getTime();
    function atualizarContador() {
      const segundos = Math.max(0, Math.ceil((expiraEm - Date.now()) / 1000));
      if (segundos === 0) {
        contador.textContent = "Reserva expirada. A disponibilidade será verificada ao continuar.";
        return;
      }
      const minutos = String(Math.floor(segundos / 60)).padStart(2, "0");
      contador.textContent = minutos + ":" + String(segundos % 60).padStart(2, "0");
    }
    atualizarContador();
    const intervalo = window.setInterval(function () {
      atualizarContador();
      if (Date.now() >= expiraEm) window.clearInterval(intervalo);
    }, 1000);
  }

  const novoEndereco = document.getElementById("checkout-novo-endereco");
  if (novoEndereco) {
    function selecionarEndereco() {
      const selecionado = document.querySelector('input[name="endereco_id"]:checked');
      const novo = selecionado && selecionado.value === "novo";
      novoEndereco.hidden = !novo;
      novoEndereco.disabled = !novo;
      document.querySelectorAll(".checkout-opcao").forEach(function (opcao) {
        opcao.classList.toggle("selecionada", opcao.contains(selecionado));
      });
    }
    document.querySelectorAll('input[name="endereco_id"]').forEach(function (campo) {
      campo.addEventListener("change", selecionarEndereco);
    });
    selecionarEndereco();
  }

  const consultar = document.getElementById("checkout-consultar-cep");
  if (consultar) {
    const cep = document.getElementById("id_cep");
    cep.addEventListener("input", function () {
      const digitos = cep.value.replace(/\D/g, "").slice(0, 8);
      cep.value = digitos.length > 5 ? digitos.slice(0, 5) + "-" + digitos.slice(5) : digitos;
    });
    consultar.addEventListener("click", async function () {
      const mensagem = document.getElementById("checkout-feedback-cep");
      consultar.disabled = true;
      mensagem.textContent = "Consultando CEP…";
      try {
        const resposta = await fetch(consultar.dataset.url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('[name="csrfmiddlewaretoken"]').value,
          },
          body: JSON.stringify({ cep: cep.value }),
        });
        const dados = await resposta.json();
        if (!resposta.ok || !dados.sucesso) {
          mensagem.textContent = dados.erro || "Não foi possível consultar o CEP.";
          return;
        }
        ["cep", "logradouro", "bairro", "cidade", "uf"].forEach(function (nome) {
          document.getElementById("id_" + nome).value = dados.endereco[nome] || "";
        });
        mensagem.textContent = "Endereço preenchido. Informe o número e confira os dados.";
        document.getElementById("id_numero").focus();
      } catch (erro) {
        mensagem.textContent = "Não foi possível consultar o CEP. Preencha o endereço ou tente novamente.";
      } finally {
        consultar.disabled = false;
      }
    });
  }
});
