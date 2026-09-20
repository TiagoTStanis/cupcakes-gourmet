document.querySelectorAll('[data-forca-senha]').forEach((campo) => {
  const indicador = document.getElementById('forca-senha');
  if (!indicador) return;
  campo.addEventListener('input', () => {
    const senha = campo.value;
    const requisitos = [senha.length >= 8, /\p{Lu}/u.test(senha), /\p{Nd}/u.test(senha)];
    const pontos = requisitos.filter(Boolean).length;
    let nivel = 'fraca';
    let texto = 'Fraca — use 8 caracteres, uma maiúscula e um número.';
    if (pontos === 3) {
      nivel = 'media';
      texto = 'Média — atende aos requisitos mínimos.';
      if (senha.length >= 12 && /[^\p{L}\p{N}]/u.test(senha)) {
        nivel = 'forte';
        texto = 'Forte — senha longa e com caracteres variados.';
      }
    }
    indicador.dataset.nivel = nivel;
    indicador.textContent = texto;
  });
});
