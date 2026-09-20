# Revisão do Planejamento e Escopo do PITE II

Este documento consolida a evolução do projeto **Cupcakes Gourmet** entre o planejamento teórico entregue na disciplina de PITE I e o sistema funcional implementado no PITE II. Apresento aqui os objetivos cumpridos, a revisão crítica dos erros e lacunas do meu documento anterior, as decisões técnicas adotadas, o backlog final detalhado e os riscos conhecidos da aplicação.

---

## 1. Objetivo e Escopo do PITE II

O objetivo principal do PITE II foi transformar a especificação conceitual do PITE I em uma aplicação web de comércio eletrônico completa, funcional e orientada a dispositivos móveis (*mobile-first*), voltada para atender confeitarias artesanais.

Todas as **18 histórias de usuário (US01 a US18)** planejadas foram integralmente implementadas em código-fonte, contemplando desde o autoatendimento do cliente até o gerenciamento operacional pela equipe da confeitaria.

### 1.1. Recursos Implementados em Ambiente Simulado

Por se tratar de um projeto acadêmico de graduação sem fins comerciais e sem orçamento para contratação de serviços corporativos em nuvem, optei por simular de maneira realista determinados fluxos externos, mantendo a integridade matemática e lógica das regras de negócio:

- **Pagamento por Cartão de Crédito e PIX**: não utilizei gateways pagos (como Mercado Pago, Pagar.me ou Stripe). Toda a lógica foi implementada no código em `pedidos/services/pagamento_service.py`: validação do número do cartão via algoritmo de Luhn, conferência de data de validade e código de segurança (CVV), cálculo de parcelas com fórmula exata de juros compostos e geração de payload SVG/chave fictícia de PIX com 30 minutos de validade. Na tela, o cliente recebe avisos claros de simulação acadêmica e pode alternar entre cartões de teste que aprovam ou recusam a compra.
- **Notificações Internas**: em vez de configurar infraestrutura de notificações push para smartphones (Firebase Cloud Messaging ou OneSignal), criei o modelo `Notificacao` no banco de dados. Os avisos de avanço de status são gerados automaticamente e disponibilizados na área de perfil do cliente e no ícone de sino no cabeçalho.
- **Envio de E-mails em Modo Demonstração**: para viabilizar a avaliação do sistema online no PythonAnywhere sem depender de credenciais de servidor SMTP, configurei a variável `MODO_DEMO` (padrão `True`). Quando ativa, os links gerados para ativação de conta e redefinição de senha são exibidos na própria página dentro de um alerta visual em destaque azul. Quando `MODO_DEMO` é desativado, o sistema despacha os e-mails normalmente via backend padrão do Django.
- **Cálculo de Frete Regional**: em vez de integrar APIs pagas ou complexas de transportadoras, estruturei uma tabela própria de valores e prazos por unidade federativa no modelo `TabelaFreteUF` (cobrindo PR, SC, RS, SP, RJ e MG). O preenchimento automático de logradouro, bairro e cidade consome a API pública e gratuita do ViaCEP, e a regra de frete grátis para compras acima de R$ 150,00 após aplicação de cupom foi implementada em `pedidos/services/frete_service.py`.

---

## 2. O que Revisei do PITE I e por que

Ao iniciar a implementação no PITE II, fiz uma leitura aprofundada dos artefatos conceituais que elaborei no PITE I. Identifiquei equívocos matemáticos, omissões de modelos essenciais, incoerências conceituais e falhas de diagramação que precisavam de correção imediata para que o sistema pudesse ser construído com consistência.

Abaixo, listo detalhadamente cada erro identificado e a solução técnica adotada no código e nos modelos:

### 2.1. Erro na Soma dos Pontos de História (54 pontos em vez de 53)
- **Problema no PITE I**: Registrei no planejamento original que o backlog somava 53 pontos de história. No entanto, ao recalcular o esforço de cada entrega, percebi que cometi um erro aritmético na Sprint 4: as histórias daquela sprint somavam 24 pontos, e não 23. Consequentemente, o total real do projeto é de 54 pontos.
- **Solução no PITE II**: Corrigi formalmente a contagem de pontos em todas as tabelas de backlog, cronograma e relatórios de acompanhamento, mantendo a soma exata de 54 pontos distribuídos nas 18 histórias.

### 2.2. Lacunas Estruturais no Diagrama de Classes Original
- **Problema no PITE I**: O diagrama conceitual do PITE I continha apenas 8 entidades básicas (`Usuario`, `Endereco`, `Produto`, `Categoria`, `Pedido`, `ItemPedido`, `Pagamento`, `Entrega`) e não sustentava as regras de negócio reais do sistema. Faltavam entidades e atributos fundamentais:
  - Não existiam `Carrinho` nem `ItemCarrinho` (o que impossibilitava salvar compras em andamento de forma persistente);
  - Não existiam `Cupom` nem `CupomUso` (impossibilitando controle de descontos e bloqueio de reuso pelo mesmo cliente);
  - Não havia diferenciação de perfil de administrador no modelo de usuário;
  - Não havia campo de controle de unidades físicas em estoque na entidade de produto;
  - Faltavam campos de segurança para ativação de conta por e-mail, contador de falhas de autenticação e bloqueio temporário de login;
  - Faltavam campos para tokens e prazos de expiração de recuperação de senha;
  - Não existia histórico auditável com data e hora de cada transição de status do pedido;
  - Não existia controle de reserva temporária de estoque durante o processo de checkout.
- **Solução no PITE II**: Reformulei a arquitetura de dados e implementei 11 tabelas físicas no banco SQLite:
  - Criei `Carrinho` e `ItemCarrinho` no app `carrinho`, vinculando o carrinho ao usuário logado;
  - Criei `Cupom` e `CupomUso` no app `pedidos`, com regras de expiração, compra mínima e registro de uso por chave estrangeira;
  - Adicionei os campos `is_staff`, `email_confirmado`, `token_confirmacao`, `token_recuperacao`, `token_recuperacao_expira`, `tentativas_login_falhas` e `bloqueado_ate` no modelo `Usuario`;
  - Adicionei `estoque` (quantidade física) e `total_vendas` no modelo `Produto`;
  - Criei o modelo `HistoricoStatus` no app `pedidos`, gravando cada mudança de estágio com carimbo de data e hora;
  - Criei o modelo `ReservaEstoque` no app `pedidos`, permitindo reservar temporariamente os produtos no momento do checkout e expirar essas reservas sob demanda.

### 2.3. Ambiguidade na Nomenclatura do Soft Delete
- **Problema no PITE I**: Uma das regras de negócio descrevia que os produtos desativados teriam o atributo `ativo=False`, enquanto em outras seções do texto o atributo era chamado de `disponivel`.
- **Solução no PITE II**: Padronizei o modelo `Produto` com o campo booleano `ativo` (padrão `True`). Implementei o *soft delete* no método `delete()` do modelo e criei o manager customizado `ProdutoManager.ativos()` para filtrar a vitrine pública, garantindo que cupcakes excluídos saiam do catálogo sem quebrar chaves estrangeiras em compras anteriores.

### 2.4. Casos de Uso Incompletos e Caso de Uso Desconectado
- **Problema no PITE I**: A especificação de casos de uso omitiu fluxos de valor essenciais, como "Recuperar Senha", "Filtrar por Categoria", "Aplicar Cupom", "Calcular Frete" e "Pagar via PIX". Em contrapartida, continha um caso de uso chamado "Gerar Relatórios Gerenciais" para o qual não existia nenhuma história de usuário ou requisito no backlog.
- **Solução no PITE II**: Excluí o caso de uso fantasma de relatórios analíticos, alinhando o escopo estritamente às necessidades da confeitaria. Mapeei e implementei os serviços e rotas dedicadas para redefinição de senha (`/usuarios/esqueci-senha/`), filtros por categoria (`/?categoria=slug`), cupons (`/pedidos/cupom/aplicar/`), cálculo de frete (`/pedidos/cep/consultar/`) e pagamento via PIX (`/pedidos/checkout/confirmar/`).

### 2.5. Diagrama de Sequência Restrito Exclusivamente a Cartão
- **Problema no PITE I**: O diagrama de sequência do processo de compra (UC01) cobria apenas a autorização com cartão de crédito, ignorando a possibilidade de pagamento à vista via PIX.
- **Solução no PITE II**: Modelei no sistema fluxos distintos para cada meio de pagamento:
  - No cartão de crédito, o pedido só é persistido se a simulação do cartão for aprovada;
  - No PIX, o pedido é criado imediatamente com status `AGUARDANDO_PAGAMENTO`, a reserva de estoque é estendida para 30 minutos e o cliente dispõe de um botão para simular a liquidação bancária. Ambos os fluxos estão implementados e cobertos por testes unitários.

### 2.6. Incoerência no Mapa Navegacional (Acesso de Visitantes)
- **Problema no PITE I**: O mapa navegacional desenhado no PITE I exigia que o usuário fizesse login ou cadastro logo na primeira tela para conseguir visualizar a loja, o que contradizia a própria história US04, que definia a vitrine como aberta a visitantes.
- **Solução no PITE II**: Configurei as rotas `/` e `/inicio/` como públicas no Django. Qualquer visitante pode explorar os cupcakes, aplicar filtros e consultar detalhes. O redirecionamento para login só é acionado quando o usuário tenta adicionar itens ao carrinho ou iniciar o checkout, utilizando o parâmetro `next` para retornar o cliente exatamente à página onde estava após se autenticar.

### 2.7. Ausência do Estado "Aguardando Pagamento" na Linha do Tempo
- **Problema no PITE I**: Embora a regra de negócio RN26 mencionasse o estado "Aguardando Pagamento", a linha do tempo desenhada para o rastreamento do pedido começava diretamente em "Pagamento Confirmado".
- **Solução no PITE II**: Incluí `AGUARDANDO_PAGAMENTO` como o status inicial no modelo `Pedido` e na tupla de opções de status. Quando o cliente opta por PIX, o pedido permanece nesse estágio com temporizador de 30 minutos, e a linha do tempo da tela `/pedidos/pedido/<numero>/` reflete esse estado com precisão.

### 2.8. Falhas nos Wireframes (Rótulos Sobrepostos e Recurso sem História)
- **Problema no PITE I**: Os wireframes originais apresentavam problemas visuais de sobreposição de rótulos em resoluções estreitas (360px a 400px) e exibiam uma seção de "Avaliações e Comentários de Clientes" para a qual não havia história de usuário nem modelo no banco.
- **Solução no PITE II**: Removi a seção de avaliações dos templates. Construí as telas em CSS puro com metodologia mobile-first, garantindo alvos de toque (*touch targets*) de no mínimo 44px, barra de navegação inferior fixa com 4 abas e apresentação limpa das informações de ingredientes e alergênicos.

---

## 3. Decisões Técnicas e Justificativas

Durante o desenvolvimento da aplicação, tomei decisões de arquitetura e tecnologia focadas em manutenibilidade, conformidade com a disciplina e viabilidade operacional:

### 3.1. Django com Arquitetura MTV e Correspondência com MVC
A disciplina de Engenharia de Software aborda amplamente o padrão arquitetural MVC (Model-View-Controller). Na implementação com Django, utilizei o padrão MTV, cuja correspondência com o MVC estruturei da seguinte forma:
- **Model**: corresponde diretamente ao **Model** do MVC. Representa a estrutura de dados, validações de modelo, regras de integridade relacional e métodos do ORM do Django.
- **View do Django**: atua como o **Controller** do MVC. É responsável por interceptar as requisições HTTP, tratar parâmetros de entrada, chamar a camada de serviços e selecionar o template HTML a ser devolvido.
- **Template**: atua como a **View** do MVC. É responsável unicamente pela renderização visual em HTML5 e CSS3, sem conter lógica de negócios.

Para manter o código modular e testável, adotei uma **camada de serviços (`services/`)** em cada aplicação do Django (`auth_service`, `busca_service`, `carrinho_service`, `frete_service`, `cupom_service`, `estoque_service`, `pagamento_service`, `pedido_service`, `historico_service` e `resumo_service`). Dessa forma, as views atuam apenas como coordenadoras de tráfego, enquanto toda a lógica de domínio reside em funções e classes isoladas.

### 3.2. Banco de Dados SQLite
Optei pelo **SQLite** (`db.sqlite3`) por ser uma solução leve, nativa do ecossistema Python, sem custo financeiro e perfeitamente adequada para protótipos acadêmicos e lojas de pequeno porte. Ele simplifica a execução local e atende integralmente aos requisitos do plano gratuito do PythonAnywhere sem requerer instâncias dedicadas de servidores de banco de dados.

### 3.3. Testes com pytest e pytest-django
Substituí o executor padrão do Django pelo **pytest** integrado com o plugin **pytest-django**. A escolha se deu pela sintaxe limpa de *asserts*, pelo sistema avançado de fixtures (`usuario_cliente`, `carrinho_com_itens`, `tabela_frete` etc.) centralizadas em `tests/conftest.py` e pela facilidade de reutilização do banco de teste (`--reuse-db`), proporcionando agilidade na verificação contínua do código.

### 3.4. Hospedagem Gratuita no PythonAnywhere
Configurei a aplicação para publicação no plano gratuito do **PythonAnywhere**. O arquivo `settings.py` lê configurações sensíveis (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `MODO_DEMO`) de um arquivo `.env` via `python-dotenv`. A coleta de arquivos estáticos com `collectstatic` e o mapeamento de diretórios `/static/` e `/media/` garantem total compatibilidade com o servidor WSGI da plataforma.

### 3.5. Autenticação Baseada em Sessão Nativa do Django
Em vez de implementar autenticação por tokens JWT (JSON Web Tokens), optei pelo mecanismo nativo de **sessões do Django** armazenadas em cookies seguros (`sessionid`). Como o Cupcakes Gourmet é uma aplicação renderizada no servidor (*Server-Side Rendering* - SSR) e não uma SPA desacoplada, a autenticação por sessão é mais segura, simples de manter e possui proteção contra CSRF nativamente configurada em todos os formulários.

### 3.6. Modo Demonstração (`MODO_DEMO`)
Criei o parâmetro `MODO_DEMO` nas variáveis de ambiente. Quando ativo, o link de ativação de conta gerado no cadastro e o link de recuperação de senha gerado no "Esqueci minha senha" são renderizados diretamente no template dentro de um card azul informativo. Essa escolha permite que professores e avaliadores testem todas as jornadas de autenticação em ambiente online sem a necessidade de um servidor de e-mail corporativo em produção.

### 3.7. Reserva Temporária de Estoque e Regras de Expiração
Para evitar que clientes tenham seus pedidos frustrados por compras simultâneas (*overselling*):
- Ao entrar no checkout, os itens do carrinho recebem uma reserva temporária de 10 minutos (`ReservaEstoque`). O cálculo do estoque disponível considera o estoque físico menos as reservas ativas não expiradas de outros usuários.
- Se o cliente escolher PIX, a reserva é automaticamente estendida para 30 minutos (tempo limite de pagamento do código).
- Adotei verificação preguiçosa (*lazy check*): em vez de depender de tarefas agendadas em segundo plano (como Celery ou cron jobs, indisponíveis no plano gratuito do PythonAnywhere), as reservas e pedidos PIX vencidos são liberados sob demanda sempre que uma consulta de estoque, adição ao carrinho ou listagem de histórico é executada.

### 3.8. Regra de Frete Grátis após Cupom
Defini que a isenção de frete é concedida estritamente para pedidos cujo subtotal de produtos supere R$ 150,00 **após o desconto do cupom**. Se um cliente tiver R$ 160,00 em cupcakes e aplicar um cupom de 10%, o subtotal líquido passa a ser R$ 144,00, mantendo a cobrança do frete por não atingir R$ 150,01. Testei deliberadamente o valor de corte exato de R$ 150,00 (paga frete) e R$ 150,01 (frete grátis).

### 3.9. Parcelamento com Juros Compostos
Para oferecer simulação realista de compras a prazo:
- De 1x até 3x: parcelamento sem acréscimo de juros;
- De 4x até 12x: aplicação de juros compostos com taxa de 2,5% ao mês sobre o total da compra (produtos menos desconto mais frete), segundo a fórmula financeira:
  $$M = P \times (1 + 0{,}025)^n$$
  Os cálculos são realizados com a classe `Decimal` do Python e arredondamento padrão para 2 casas decimais, gerando a tabela de parcelas detalhada exibida na tela de pagamento.

---

## 4. Backlog Final das 18 Histórias de Usuário

A tabela abaixo apresenta o backlog consolidado e implementado no sistema. A soma de pontos totaliza **54 pontos** (10 na Sprint 1, 7 na Sprint 2, 13 na Sprint 3 e 24 na Sprint 4, a mesma divisão do PITE I, agora com a soma correta).

| História | Pontos | Situação | Onde está no sistema (Rota ou Tela) | Testes Automatizados |
|---|:---:|:---:|---|---|
| **US01**: Cadastrar-se no aplicativo | 3 | Implementada | `/usuarios/cadastro/` e `/usuarios/ativar/<token>/` | `tests/test_usuarios.py` |
| **US02**: Entrar na conta | 2 | Implementada | `/usuarios/login/` e `/usuarios/logout/` | `tests/test_usuarios.py` |
| **US03**: Recuperar acesso à conta | 2 | Implementada | `/usuarios/esqueci-senha/` e `/usuarios/redefinir/<token>/` | `tests/test_usuarios.py` |
| **US04**: Ver o catálogo de cupcakes | 3 | Implementada | `/` (vitrine) | `tests/test_catalogo.py` |
| **US05**: Filtrar por categoria | 2 | Implementada | `/?categoria=<slug>` na vitrine | `tests/test_catalogo.py` |
| **US06**: Buscar cupcakes pelo nome | 2 | Implementada | `/busca/` e `/busca/api/` | `tests/test_catalogo.py` |
| **US07**: Ver detalhes de um cupcake | 2 | Implementada | `/produto/<slug>/` | `tests/test_catalogo.py` |
| **US08**: Adicionar cupcakes ao carrinho | 3 | Implementada | `/carrinho/adicionar/` (botão na página do produto) | `tests/test_carrinho.py` |
| **US09**: Gerenciar itens do carrinho | 2 | Implementada | `/carrinho/`, `/carrinho/alterar/` e `/carrinho/remover/` | `tests/test_carrinho.py` |
| **US10**: Calcular o frete antes de pagar | 3 | Implementada | `/pedidos/cep/consultar/` (campo de CEP no carrinho) | `tests/test_frete_cupom.py` |
| **US11**: Finalizar o pedido | 5 | Implementada | `/pedidos/checkout/`, `/pedidos/checkout/pagamento/` e `/pedidos/checkout/resumo/` | `tests/test_estoque_checkout.py` |
| **US12**: Pagar com cartão de crédito | 5 | Implementada | `/pedidos/checkout/confirmar/` (opção Cartão) | `tests/test_pagamento_pedido.py` |
| **US13**: Pagar com PIX | 3 | Implementada | `/pedidos/checkout/confirmar/` (opção PIX) e `/pedidos/pedido/<numero>/confirmar-pix/` | `tests/test_pagamento_pedido.py` |
| **US14**: Usar cupom de desconto | 2 | Implementada | `/pedidos/cupom/aplicar/` e `/pedidos/cupom/remover/` | `tests/test_frete_cupom.py` |
| **US15**: Acompanhar o status do pedido | 3 | Implementada | `/pedidos/pedido/<numero>/` e `/pedidos/notificacoes/` | `tests/test_status_notificacoes.py` |
| **US16**: Consultar histórico de pedidos | 2 | Implementada | `/pedidos/` e `/pedidos/pedido/<numero>/repetir/` | `tests/test_historico.py` |
| **US17**: Gerenciar produtos do catálogo (administrador) | 5 | Implementada | `/painel/produtos/` e `/painel/categorias/` | `tests/test_painel.py` |
| **US18**: Gerenciar pedidos recebidos (administrador) | 5 | Implementada | `/painel/pedidos/`, `/painel/pedidos/<numero>/avancar/` e `/painel/pedidos/<numero>/cancelar/` | `tests/test_painel.py` |
| **TOTAL** | **54** | **18 Concluídas** | | |

---

## 5. Riscos e Limitações Conhecidos

Como estudante de Engenharia de Software, reconheço com transparência as limitações técnicas do projeto em seu estágio atual e os riscos inerentes à arquitetura adotada:

1. **Concorrência e Bloqueio de Arquivo no SQLite**: o SQLite opera com travamento em nível de arquivo durante operações de escrita. Em um cenário real com centenas de clientes simultâneos realizando checkout no mesmo segundo, poderiam ocorrer erros de *database is locked*. Para um ambiente de produção em larga escala, a mitigação recomendada seria migrar para um SGBD cliente-servidor robusto (PostgreSQL) e utilizar travas pessimistas no ORM com `select_for_update()`.
2. **Expiração Preguiçosa (*Lazy Check*) de Reservas e PIX**: a limpeza de reservas vencidas e o cancelamento de pedidos PIX não pagos dependem de requisições disparadas pelos usuários. Se a loja ficar sem acessos durante uma madrugada, um pedido PIX expirado permanecerá com status `AGUARDANDO_PAGAMENTO` até que o cliente ou um administrador abra a tela de pedidos. Em produção comercial, esse controle deve ser executado por um serviço agendado independente (como Celery com Redis ou agendador cron no servidor).
3. **Pagamento em Ambiente Acadêmico Controlado**: os cálculos de validação e simulação são matematicamente rigorosos, mas não há conexão com operadoras financeiras reais. Nenhuma cobrança financeira é executada, e a entrega de produtos para clientes reais exigiria a substituição do serviço `pagamento_service.py` por SDKs homologados de instituições bancárias.
4. **Dependência da API Pública do ViaCEP**: a busca de endereços depende da estabilidade do serviço gratuito do ViaCEP. Para mitigar indisponibilidades de rede, configurei um timeout seguro de 3 segundos com tratamento de exceções específicas, permitindo ao usuário continuar o cadastro mesmo se o preenchimento automático falhar temporariamente.
5. **Cobertura Geográfica Restrita do Frete**: a tabela própria cobre atualmente seis estados das regiões Sul e Sudeste (PR, SC, RS, SP, RJ e MG). Entregas para outros estados exibem mensagem informando a indisponibilidade temporária de rota até que novas tabelas sejam cadastradas pela equipe da confeitaria.
