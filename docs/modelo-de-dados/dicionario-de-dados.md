# Dicionário de dados

Gerado a partir dos modelos e do banco real do sistema (SQLite). Cada tabela lista as colunas, o tipo físico, se aceita nulo, a chave e o domínio dos valores.

## usuarios_usuario

Modelo `Usuario` do app `usuarios`: usuário.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| password | VARCHAR(128) | não |  |  | senha |
| last_login | DATETIME | sim |  |  | último login |
| is_superuser | BOOLEAN | não |  | padrao False | status de superusuário |
| email | VARCHAR(254) | não | UNICO |  | e-mail |
| nome_completo | VARCHAR(150) | não |  |  | Nome completo do cliente ou administrador |
| telefone | VARCHAR(20) | não |  |  | Telefone de contato (opcional) |
| email_confirmado | BOOLEAN | não |  | padrao False | Indica se o link de ativação já foi usado; sem isso o login é bloqueado |
| token_confirmacao | VARCHAR(64) | sim |  |  | Hash do token de ativação de conta (o token em si nunca é guardado) |
| token_recuperacao | VARCHAR(64) | sim |  |  | Hash do token de redefinição de senha, de uso único |
| token_recuperacao_expira | DATETIME | sim |  |  | Data e hora em que o token de redefinição deixa de valer (60 minutos) |
| tentativas_login_falhas | INTEGER (>= 0) | não |  | minimo 0; padrao 0 | Erros de senha seguidos; ao chegar em 3 a conta é bloqueada |
| bloqueado_ate | DATETIME | sim |  |  | Fim do bloqueio de 15 minutos por excesso de erros de senha |
| is_active | BOOLEAN | não |  | padrao True | Conta ativa no sistema |
| is_staff | BOOLEAN | não |  | padrao False | Perfil de administrador: dá acesso ao painel |
| criado_em | DATETIME | não |  |  | Data e hora de criação |

## usuarios_endereco

Modelo `Endereco` do app `usuarios`: endereco.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| usuario_id | INTEGER (FK) | não | FK -> usuarios_usuario |  | Referência a usuário |
| cep | VARCHAR(9) | não |  |  | CEP |
| logradouro | VARCHAR(150) | não |  |  | Rua, avenida ou similar do endereço |
| numero | VARCHAR(20) | não |  |  | Número legível do pedido, exibido ao cliente |
| complemento | VARCHAR(100) | não |  |  | Complemento do endereço (opcional) |
| bairro | VARCHAR(80) | não |  |  | Bairro do endereço |
| cidade | VARCHAR(80) | não |  |  | Cidade do endereço |
| uf | VARCHAR(2) | não |  |  | UF |
| principal | BOOLEAN | não |  | padrao True | Endereço preferido do cliente |

## catalogo_categoria

Modelo `Categoria` do app `catalogo`: categoria.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| nome | VARCHAR(100) | não | UNICO |  | nome |
| slug | VARCHAR(100) | não | UNICO |  | Texto único para uso na URL (gerado do nome) |
| ativa | BOOLEAN | não |  | padrao True | Categoria visível na vitrine |

## catalogo_produto

Modelo `Produto` do app `catalogo`: produto.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| categoria_id | INTEGER (FK) | não | FK -> catalogo_categoria |  | Referência a categoria |
| nome | VARCHAR(150) | não |  |  | nome |
| slug | VARCHAR(150) | não | UNICO |  | Texto único para uso na URL (gerado do nome) |
| descricao | TEXT | não |  |  | descrição |
| ingredientes | TEXT | não |  |  | Lista de ingredientes exibida na página do produto |
| alergenicos | TEXT | não |  |  | alergênicos |
| preco | DECIMAL(8,2) | não |  | minimo 0.01 | preço |
| imagem | VARCHAR(100) (caminho do arquivo) | sim |  |  | Caminho da foto do cupcake (JPG ou PNG, até 5 MB) |
| estoque | INTEGER (>= 0) | não |  | minimo 0; padrao 0 | Unidades disponíveis para venda |
| total_vendas | INTEGER (>= 0) | não |  | minimo 0; padrao 0 | total de vendas |
| ativo | BOOLEAN | não |  | padrao True | Registro ativo; falso significa desativado (exclusão lógica, o registro é mantido) |
| criado_em | DATETIME | não |  |  | Data e hora de criação |
| atualizado_em | DATETIME | não |  |  | Data e hora da última alteração |
| nome_busca | VARCHAR(150) | não |  |  | nome para busca |

## carrinho_carrinho

Modelo `Carrinho` do app `carrinho`: carrinho.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| usuario_id | INTEGER (FK, unico) | não | FK -> usuarios_usuario |  | Referência a usuário |
| criado_em | DATETIME | não |  |  | Data e hora de criação |
| atualizado_em | DATETIME | não |  |  | Data e hora da última alteração |

## carrinho_itemcarrinho

Modelo `ItemCarrinho` do app `carrinho`: item do carrinho.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| carrinho_id | INTEGER (FK) | não | FK -> carrinho_carrinho |  | Referência a carrinho |
| produto_id | INTEGER (FK) | não | FK -> catalogo_produto |  | Referência a produto |
| quantidade | INTEGER (>= 0) | não |  | minimo 0; padrao 1 | Quantidade de unidades |
| criado_em | DATETIME | não |  |  | Data e hora de criação |

## pedidos_tabelafreteuf

Modelo `TabelaFreteUF` do app `pedidos`: tabela de frete por UF.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| uf | VARCHAR(2) | não | UNICO |  | UF |
| valor | DECIMAL(6,2) | não |  |  | Valor em reais (ou percentual, no caso de cupom percentual) |
| prazo_dias | INTEGER (>= 0) | não |  | minimo 0 | prazo em dias |

## pedidos_cupom

Modelo `Cupom` do app `pedidos`: cupom.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| codigo | VARCHAR(30) | não | UNICO |  | código |
| tipo | VARCHAR(10) | não |  | valores: PERCENTUAL, FIXO | Tipo do desconto: percentual ou valor fixo |
| valor | DECIMAL(6,2) | não |  |  | Valor em reais (ou percentual, no caso de cupom percentual) |
| valor_minimo_pedido | DECIMAL(8,2) | não |  | padrao Decimal('0.00') | valor mínimo do pedido |
| data_validade | DATETIME | não |  |  | Data limite de validade |
| ativo | BOOLEAN | não |  | padrao True | Registro ativo; falso significa desativado (exclusão lógica, o registro é mantido) |

## pedidos_cupomuso

Modelo `CupomUso` do app `pedidos`: uso de cupom.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| cupom_id | INTEGER (FK) | não | FK -> pedidos_cupom |  | Referência a cupom |
| usuario_id | INTEGER (FK) | não | FK -> usuarios_usuario |  | Referência a usuário |
| data_uso | DATETIME | não |  |  | data de uso |

## pedidos_reservaestoque

Modelo `ReservaEstoque` do app `pedidos`: reserva estoque.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| usuario_id | INTEGER (FK) | não | FK -> usuarios_usuario |  | Referência a usuário |
| produto_id | INTEGER (FK) | não | FK -> catalogo_produto |  | Referência a produto |
| quantidade | INTEGER (>= 0) | não |  | minimo 0 | Quantidade de unidades |
| criada_em | DATETIME | não |  |  | Data e hora de criação |
| expira_em | DATETIME | não |  |  | Data e hora em que a reserva de estoque deixa de valer |
| ativa | BOOLEAN | não |  | padrao True | Categoria visível na vitrine |

## pedidos_pedido

Modelo `Pedido` do app `pedidos`: pedido.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| numero | VARCHAR(20) | não | UNICO |  | Número legível do pedido, exibido ao cliente |
| usuario_id | INTEGER (FK) | não | FK -> usuarios_usuario |  | Referência a usuário |
| endereco_entrega | TEXT | não |  |  | Cópia do endereço no momento da compra (não muda se o cliente editar o cadastro) |
| subtotal | DECIMAL(8,2) | não |  |  | Soma dos itens, antes de desconto e frete |
| valor_desconto | DECIMAL(8,2) | não |  | padrao Decimal('0.00') | Desconto do cupom, aplicado antes do frete |
| cupom_id | INTEGER (FK) | sim | FK -> pedidos_cupom |  | Referência a cupom |
| valor_frete | DECIMAL(6,2) | não |  |  | Frete calculado pela tabela por UF (zero quando o subtotal após o cupom passa de R$ 150,00) |
| valor_total | DECIMAL(8,2) | não |  |  | Valor final cobrado: subtotal, menos desconto, mais frete (mais juros de parcelamento) |
| forma_pagamento | VARCHAR(6) | não |  | valores: CARTAO, PIX | Cartão de crédito ou PIX (ambos simulados) |
| status | VARCHAR(20) | não |  | valores: AGUARDANDO_PAGAMENTO, PAGAMENTO_CONFIRMADO, EM_PREPARACAO, SAIU_PARA_ENTREGA, ENTREGUE, CANCELADO; padrao 'AGUARDANDO_PAGAMENTO' | Etapa em que o pedido se encontra |
| estoque_baixado | BOOLEAN | não |  | padrao False | Indica se o estoque já foi baixado; evita baixar ou repor duas vezes |
| pix_expira_em | DATETIME | sim |  |  | Fim da validade do PIX (30 minutos); vazio para outras formas de pagamento |
| detalhes_pagamento | JSON (TEXT) | não |  |  | Dados da simulação: parcelas, últimos 4 dígitos e código PIX fictício. Nunca guarda o número completo do cartão |
| criado_em | DATETIME | não |  |  | Data e hora de criação |
| atualizado_em | DATETIME | não |  |  | Data e hora da última alteração |

## pedidos_itempedido

Modelo `ItemPedido` do app `pedidos`: item pedido.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| pedido_id | INTEGER (FK) | não | FK -> pedidos_pedido |  | Referência a pedido |
| produto_id | INTEGER (FK) | não | FK -> catalogo_produto |  | Referência a produto |
| nome_produto | VARCHAR(150) | não |  |  | Nome do produto no momento da compra |
| preco_unitario | DECIMAL(8,2) | não |  |  | Preço de uma unidade no momento da compra |
| quantidade | INTEGER (>= 0) | não |  | minimo 0 | Quantidade de unidades |
| subtotal | DECIMAL(8,2) | não |  |  | Soma dos itens, antes de desconto e frete |

## pedidos_historicostatus

Modelo `HistoricoStatus` do app `pedidos`: historico status.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| pedido_id | INTEGER (FK) | não | FK -> pedidos_pedido |  | Referência a pedido |
| status | VARCHAR(20) | não |  | valores: AGUARDANDO_PAGAMENTO, PAGAMENTO_CONFIRMADO, EM_PREPARACAO, SAIU_PARA_ENTREGA, ENTREGUE, CANCELADO | Etapa em que o pedido se encontra |
| criado_em | DATETIME | não |  |  | Data e hora de criação |

## pedidos_notificacao

Modelo `Notificacao` do app `pedidos`: notificacao.

| Coluna | Tipo | Nulo | Chave | Domínio / regra | Descrição |
|---|---|---|---|---|---|
| id | INTEGER (PK, auto) | não | PK |  | Identificador único do registro |
| usuario_id | INTEGER (FK) | não | FK -> usuarios_usuario |  | Referência a usuário |
| pedido_id | INTEGER (FK) | sim | FK -> pedidos_pedido |  | Referência a pedido |
| titulo | VARCHAR(100) | não |  |  | Título curto da notificação |
| mensagem | TEXT | não |  |  | Texto da notificação |
| lida | BOOLEAN | não |  | padrao False | Indica se o cliente já abriu a notificação |
| criada_em | DATETIME | não |  |  | Data e hora de criação |

