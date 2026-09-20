-- Modelo físico (SQLite) do Cupcakes Gourmet
-- Extraído do banco após aplicar todas as migrações.

CREATE TABLE "carrinho_carrinho" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "criado_em" datetime NOT NULL, "atualizado_em" datetime NOT NULL, "usuario_id" bigint NOT NULL UNIQUE REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "carrinho_itemcarrinho" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "quantidade" integer unsigned NOT NULL CHECK ("quantidade" >= 0), "criado_em" datetime NOT NULL, "carrinho_id" bigint NOT NULL REFERENCES "carrinho_carrinho" ("id") DEFERRABLE INITIALLY DEFERRED, "produto_id" bigint NOT NULL REFERENCES "catalogo_produto" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "catalogo_categoria" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nome" varchar(100) NOT NULL UNIQUE, "slug" varchar(100) NOT NULL UNIQUE, "ativa" bool NOT NULL);

CREATE TABLE "catalogo_produto" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nome" varchar(150) NOT NULL, "slug" varchar(150) NOT NULL UNIQUE, "descricao" text NOT NULL, "ingredientes" text NOT NULL, "alergenicos" text NOT NULL, "preco" decimal NOT NULL, "imagem" varchar(100) NULL, "estoque" integer unsigned NOT NULL CHECK ("estoque" >= 0), "total_vendas" integer unsigned NOT NULL CHECK ("total_vendas" >= 0), "ativo" bool NOT NULL, "criado_em" datetime NOT NULL, "atualizado_em" datetime NOT NULL, "nome_busca" varchar(150) NOT NULL, "categoria_id" bigint NOT NULL REFERENCES "catalogo_categoria" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "pedidos_cupom" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "codigo" varchar(30) NOT NULL UNIQUE, "tipo" varchar(10) NOT NULL, "valor" decimal NOT NULL, "valor_minimo_pedido" decimal NOT NULL, "data_validade" datetime NOT NULL, "ativo" bool NOT NULL);

CREATE TABLE "pedidos_cupomuso" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "data_uso" datetime NOT NULL, "cupom_id" bigint NOT NULL REFERENCES "pedidos_cupom" ("id") DEFERRABLE INITIALLY DEFERRED, "usuario_id" bigint NOT NULL REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "pedidos_historicostatus" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "status" varchar(20) NOT NULL, "criado_em" datetime NOT NULL, "pedido_id" bigint NOT NULL REFERENCES "pedidos_pedido" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "pedidos_itempedido" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nome_produto" varchar(150) NOT NULL, "preco_unitario" decimal NOT NULL, "quantidade" integer unsigned NOT NULL CHECK ("quantidade" >= 0), "subtotal" decimal NOT NULL, "produto_id" bigint NOT NULL REFERENCES "catalogo_produto" ("id") DEFERRABLE INITIALLY DEFERRED, "pedido_id" bigint NOT NULL REFERENCES "pedidos_pedido" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "item_pedido_quantidade_positiva" CHECK ("quantidade" > 0));

CREATE TABLE "pedidos_notificacao" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "titulo" varchar(100) NOT NULL, "mensagem" text NOT NULL, "lida" bool NOT NULL, "criada_em" datetime NOT NULL, "pedido_id" bigint NULL REFERENCES "pedidos_pedido" ("id") DEFERRABLE INITIALLY DEFERRED, "usuario_id" bigint NOT NULL REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "pedidos_pedido" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "numero" varchar(20) NOT NULL UNIQUE, "endereco_entrega" text NOT NULL, "subtotal" decimal NOT NULL, "valor_desconto" decimal NOT NULL, "valor_frete" decimal NOT NULL, "valor_total" decimal NOT NULL, "forma_pagamento" varchar(6) NOT NULL, "status" varchar(20) NOT NULL, "estoque_baixado" bool NOT NULL, "pix_expira_em" datetime NULL, "detalhes_pagamento" text NOT NULL CHECK ((JSON_VALID("detalhes_pagamento") OR "detalhes_pagamento" IS NULL)), "criado_em" datetime NOT NULL, "atualizado_em" datetime NOT NULL, "cupom_id" bigint NULL REFERENCES "pedidos_cupom" ("id") DEFERRABLE INITIALLY DEFERRED, "usuario_id" bigint NOT NULL REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "pedidos_reservaestoque" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "quantidade" integer unsigned NOT NULL CHECK ("quantidade" >= 0), "criada_em" datetime NOT NULL, "expira_em" datetime NOT NULL, "ativa" bool NOT NULL, "produto_id" bigint NOT NULL REFERENCES "catalogo_produto" ("id") DEFERRABLE INITIALLY DEFERRED, "usuario_id" bigint NOT NULL REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "reserva_usuario_produto_unica" UNIQUE ("usuario_id", "produto_id"), CONSTRAINT "reserva_quantidade_positiva" CHECK ("quantidade" > 0));

CREATE TABLE "pedidos_tabelafreteuf" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "uf" varchar(2) NOT NULL UNIQUE, "valor" decimal NOT NULL, "prazo_dias" integer unsigned NOT NULL CHECK ("prazo_dias" >= 0));

CREATE TABLE "usuarios_endereco" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "cep" varchar(9) NOT NULL, "logradouro" varchar(150) NOT NULL, "numero" varchar(20) NOT NULL, "complemento" varchar(100) NOT NULL, "bairro" varchar(80) NOT NULL, "cidade" varchar(80) NOT NULL, "uf" varchar(2) NOT NULL, "principal" bool NOT NULL, "usuario_id" bigint NOT NULL REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "usuarios_usuario" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "password" varchar(128) NOT NULL, "last_login" datetime NULL, "is_superuser" bool NOT NULL, "email" varchar(254) NOT NULL UNIQUE, "nome_completo" varchar(150) NOT NULL, "telefone" varchar(20) NOT NULL, "email_confirmado" bool NOT NULL, "token_confirmacao" varchar(64) NULL, "token_recuperacao" varchar(64) NULL, "token_recuperacao_expira" datetime NULL, "tentativas_login_falhas" integer unsigned NOT NULL CHECK ("tentativas_login_falhas" >= 0), "bloqueado_ate" datetime NULL, "is_active" bool NOT NULL, "is_staff" bool NOT NULL, "criado_em" datetime NOT NULL);

CREATE TABLE "usuarios_usuario_groups" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "usuario_id" bigint NOT NULL REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "usuarios_usuario_user_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "usuario_id" bigint NOT NULL REFERENCES "usuarios_usuario" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "carrinho_itemcarrinho_carrinho_id_959a5387" ON "carrinho_itemcarrinho" ("carrinho_id");

CREATE UNIQUE INDEX "carrinho_itemcarrinho_carrinho_id_produto_id_4cb7d255_uniq" ON "carrinho_itemcarrinho" ("carrinho_id", "produto_id");

CREATE INDEX "carrinho_itemcarrinho_produto_id_c126941e" ON "carrinho_itemcarrinho" ("produto_id");

CREATE INDEX "catalogo_produto_categoria_id_773a9958" ON "catalogo_produto" ("categoria_id");

CREATE INDEX "catalogo_produto_nome_busca_7c046954" ON "catalogo_produto" ("nome_busca");

CREATE INDEX "pedidos_cupomuso_cupom_id_c3de1fac" ON "pedidos_cupomuso" ("cupom_id");

CREATE UNIQUE INDEX "pedidos_cupomuso_cupom_id_usuario_id_4585f4e2_uniq" ON "pedidos_cupomuso" ("cupom_id", "usuario_id");

CREATE INDEX "pedidos_cupomuso_usuario_id_4ca1d61a" ON "pedidos_cupomuso" ("usuario_id");

CREATE INDEX "pedidos_historicostatus_pedido_id_9a8f669c" ON "pedidos_historicostatus" ("pedido_id");

CREATE INDEX "pedidos_itempedido_pedido_id_27933cba" ON "pedidos_itempedido" ("pedido_id");

CREATE INDEX "pedidos_itempedido_produto_id_504470b9" ON "pedidos_itempedido" ("produto_id");

CREATE INDEX "pedidos_notificacao_pedido_id_5c350cce" ON "pedidos_notificacao" ("pedido_id");

CREATE INDEX "pedidos_notificacao_usuario_id_42a1f307" ON "pedidos_notificacao" ("usuario_id");

CREATE INDEX "pedidos_pedido_cupom_id_e3447f3d" ON "pedidos_pedido" ("cupom_id");

CREATE INDEX "pedidos_pedido_usuario_id_316c8bf5" ON "pedidos_pedido" ("usuario_id");

CREATE INDEX "pedidos_reservaestoque_expira_em_eb64d0fa" ON "pedidos_reservaestoque" ("expira_em");

CREATE INDEX "pedidos_reservaestoque_produto_id_f3262877" ON "pedidos_reservaestoque" ("produto_id");

CREATE INDEX "pedidos_reservaestoque_usuario_id_42d5cf30" ON "pedidos_reservaestoque" ("usuario_id");

CREATE INDEX "usuarios_endereco_usuario_id_429c82c6" ON "usuarios_endereco" ("usuario_id");

CREATE INDEX "usuarios_usuario_groups_group_id_e77f6dcf" ON "usuarios_usuario_groups" ("group_id");

CREATE INDEX "usuarios_usuario_groups_usuario_id_7a34077f" ON "usuarios_usuario_groups" ("usuario_id");

CREATE UNIQUE INDEX "usuarios_usuario_groups_usuario_id_group_id_4ed5b09e_uniq" ON "usuarios_usuario_groups" ("usuario_id", "group_id");

CREATE INDEX "usuarios_usuario_user_permissions_permission_id_4e5c0f2f" ON "usuarios_usuario_user_permissions" ("permission_id");

CREATE INDEX "usuarios_usuario_user_permissions_usuario_id_60aeea80" ON "usuarios_usuario_user_permissions" ("usuario_id");

CREATE UNIQUE INDEX "usuarios_usuario_user_permissions_usuario_id_permission_id_217cadcd_uniq" ON "usuarios_usuario_user_permissions" ("usuario_id", "permission_id");
