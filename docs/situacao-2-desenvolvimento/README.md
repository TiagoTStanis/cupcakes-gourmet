# Situação 2: desenvolvimento

O código não fica dentro de `docs/`, porque um projeto Django precisa da estrutura na raiz do repositório. Este arquivo mostra onde está cada parte.

- **Sistema em funcionamento:** https://tiagotstanis.pythonanywhere.com
- **Manual de uso:** [manual-de-uso.md](manual-de-uso.md)
- **Como rodar e testar:** veja o [README da raiz](../../README.md).

## Padrão MVC no Django

O Django usa o padrão MTV. A correspondência com o MVC da disciplina é direta:

| MVC | No Django | Onde está |
|---|---|---|
| Model | Model | `models.py` de cada app |
| Controller | View | `views.py` de cada app |
| View | Template | pasta `templates/` |

As regras de negócio ficam em uma camada de serviços, na pasta `services/` de cada app, para as views ficarem só coordenando requisição e resposta.

## Mapa do código

| Pasta | O que tem |
|---|---|
| `usuarios/` | cadastro, ativação, login com bloqueio, recuperação de senha, perfil e endereços |
| `catalogo/` | categorias, produtos, busca, vitrine e o comando `popular_dados` |
| `carrinho/` | carrinho salvo no servidor |
| `pedidos/` | frete, cupom, checkout, reserva de estoque, pagamento simulado, pedidos, notificações e histórico |
| `painel/` | painel do administrador |
| `templates/` e `static/` | telas (HTML), estilos (CSS) e scripts (JavaScript) |
| `tests/` | testes automatizados com pytest |
| `cupcakes_gourmet/` | configurações do projeto |

Front-end em HTML, CSS e JavaScript puros. Back-end em Python com Django 5.2 e banco SQLite. Bibliotecas em `requirements.txt`.
