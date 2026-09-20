# Documentação do Projeto Cupcakes Gourmet

Este diretório reúne a documentação técnica, de planejamento, de modelagem e de testes do sistema **Cupcakes Gourmet**, desenvolvido para a disciplina de Projeto Integrador Transdisciplinar em Engenharia de Software II (PITE II) da Universidade Cruzeiro do Sul.

O objetivo desta documentação é detalhar as decisões de projeto, registrar a evolução entre o planejamento inicial (PITE I) e a implementação funcional (PITE II), apresentar os modelos de dados e orientar a execução da suíte de testes e validações com usuários.

---

## Estrutura da Documentação

A documentação está organizada nos seguintes documentos temáticos:

1. [Revisão do Planejamento e Escopo (01-revisao-do-planejamento.md)](01-revisao-do-planejamento.md)
   Apresenta o escopo implementado no PITE II, a análise crítica e correção das lacunas do documento do PITE I, as justificativas arquiteturais e técnicas, o backlog final consolidado das 18 histórias de usuário e os riscos conhecidos.

2. [Modelagem UML (02-uml/)](02-uml/)
   Diagramas conceituais e comportamentais da aplicação: diagrama de classes atualizado, diagrama de casos de uso e diagramas de sequência dos fluxos de pagamento (cartão e PIX).

3. [Interação Humano-Computador e Ergonomia (03-ihc.md)](03-ihc.md)
   Estudo da interface mobile-first, mapa navegacional corrigido, wireframes revisados, paleta de cores, tipografia e diretrizes de acessibilidade e ergonomia móvel.

4. [Manual de Uso da Aplicação (04-manual-de-uso.md)](04-manual-de-uso.md)
   Guia passo a passo para o cliente (navegação, carrinho, checkout e acompanhamento de pedidos) e para o administrador da confeitaria (gestão de produtos, categorias e pedidos no painel operacional).

5. [Plano de Testes e Qualidade (05-plano-de-testes.md)](05-plano-de-testes.md)
   Estratégia de verificação e validação, documentação da suíte com 156 testes automatizados em pytest-django, matriz de rastreabilidade de requisitos, roteiro para testes com usuários e modelo em branco do laudo de qualidade.

6. [Modelo de Dados (modelo-de-dados/)](modelo-de-dados/)
   Estrutura física e lógica do banco de dados relacional (SQLite):
   - [Dicionário de Dados](modelo-de-dados/dicionario-de-dados.md): descrição de cada tabela, campo, tipo e regras de integridade.
   - [Diagrama Entidade-Relacionamento](modelo-de-dados/diagrama-er.md): representação visual dos relacionamentos entre entidades.
   - [Modelo Físico SQL](modelo-de-dados/modelo-fisico.sql): script DDL executável gerado a partir do schema real.
