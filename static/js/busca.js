document.addEventListener("DOMContentLoaded", () => {
  const campoBusca = document.getElementById("campo-busca");
  const listaResultados = document.getElementById("resultados-busca");
  const contagemResultados = document.getElementById("contagem-resultados");
  const mensagemVazio = document.getElementById("busca-vazia");

  if (!campoBusca || !listaResultados) {
    return;
  }

  let temporizador = null;

  function escaparHtml(texto) {
    return String(texto == null ? "" : texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatarPreco(valor) {
    const num = parseFloat(valor);
    return isNaN(num) ? valor : "R$ " + num.toFixed(2).replace(".", ",");
  }

  function renderizarItem(p) {
    const imagemHtml = p.imagem_url
      ? `<img src="${escaparHtml(p.imagem_url)}" alt="${escaparHtml(p.nome)}" class="produto-card-imagem">`
      : `<div class="produto-card-imagem reserva" aria-label="Foto ilustrativa"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a4 4 0 0 0-4 4v1H6a3 3 0 0 0-3 3v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-9a3 3 0 0 0-3-3h-2V6a4 4 0 0 0-4-4Z"/></svg></div>`;

    const precoFormatado = p.preco_formatado || formatarPreco(p.preco);

    return `
      <article class="produto-card">
        <a href="${escaparHtml(p.url)}" class="produto-card-link">
          ${imagemHtml}
          <div class="produto-card-corpo">
            <span class="produto-card-categoria">${escaparHtml(p.categoria)}</span>
            <h3 class="produto-card-titulo">${escaparHtml(p.nome)}</h3>
            <span class="produto-card-preco">${escaparHtml(precoFormatado)}</span>
          </div>
        </a>
      </article>
    `;
  }

  function realizarBusca(termo) {
    if (!termo) {
      listaResultados.innerHTML = "";
      if (contagemResultados) contagemResultados.textContent = "";
      if (mensagemVazio) mensagemVazio.style.display = "none";
      return;
    }

    const url = `/busca/api/?q=${encodeURIComponent(termo)}`;
    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then((res) => {
        if (!res.ok) throw new Error("Falha na consulta");
        return res.json();
      })
      .then((data) => {
        const produtos = Array.isArray(data) ? data : (data.produtos || []);
        if (contagemResultados) {
          contagemResultados.textContent = produtos.length > 0 ? `${produtos.length} resultado(s)` : "";
        }
        if (produtos.length === 0) {
          listaResultados.innerHTML = "";
          if (mensagemVazio) {
            mensagemVazio.textContent = "";
            const aviso = document.createElement("p");
            aviso.className = "vazio";
            aviso.append(`Nenhum cupcake encontrado para '${termo}'. Que tal explorar o `);
            const link = document.createElement("a");
            link.href = "/";
            link.textContent = "catálogo completo";
            aviso.append(link, "?");
            mensagemVazio.appendChild(aviso);
            mensagemVazio.style.display = "block";
          }
        } else {
          if (mensagemVazio) {
            mensagemVazio.style.display = "none";
          }
          listaResultados.innerHTML = produtos.map(renderizarItem).join("");
        }
      })
      .catch((erro) => {
        console.error("Erro na busca:", erro);
      });
  }

  campoBusca.addEventListener("input", (evento) => {
    clearTimeout(temporizador);
    const termo = evento.target.value.trim();
    temporizador = setTimeout(() => {
      realizarBusca(termo);
    }, 300);
  });
});
