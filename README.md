# Cupcakes Gourmet

Desenvolvi o **Cupcakes Gourmet** como projeto de conclusão de disciplina de graduação em desenvolvimento web. Trata-se de uma aplicação de comércio eletrônico com foco prioritário na experiência móvel (mobile-first), concebida para atender confeitarias artesanais.

## O Problema da Confeitaria

Confeitarias artesanais enfrentam desafios operacionais bem específicos no comércio digital:
- Produtos delicados e perecíveis exigem produção sob encomenda e controle rigoroso de estoque para evitar desperdício de insumos.
- O cálculo de entrega precisa considerar prazos de preparação e rotas regionais viáveis.
- Os clientes necessitam de informações claras sobre ingredientes e alergênicos, além de transparência sobre o status de produção e entrega dos pedidos.
- Plataformas de e-commerce genéricas costumam ser caras, complexas e inadequadas para a realidade de pequenos ateliês gastronômicos.

O Cupcakes Gourmet foi planejado para resolver essas necessidades por meio de uma interface direta, leve e sem atritos tanto para os clientes quanto para a equipe da confeitaria.

---

## Funcionalidades por Perfil

### Cliente e Visitante
- **Vitrine e Busca**: visualização dos produtos organizados por categorias (Clássicos, Veganos e Temáticos), ordenação por popularidade ou preço, e busca com resposta imediata (debounce de 300 ms) sem diferenciação de acentos ou maiúsculas.
- **Detalhe do Cupcake**: lista completa de ingredientes, destaque obrigatório para alergênicos e indicador de estoque em tempo real com bloqueio de compra para produtos esgotados.
- **Carrinho Persistente**: controle de itens no carrinho com limite de até 10 unidades por produto e trava contra quantidades superiores ao estoque físico. O carrinho fica vinculado à conta do cliente no banco de dados.
- **Autenticação Segura**: cadastro com confirmação de conta por token de uso único, recuperação de senha com validade de 60 minutos e bloqueio temporário de 15 minutos após três falhas consecutivas de login.
- **Checkout em 3 Etapas**: fluxo otimizado para dispositivos móveis dividido em seleção de endereço (com busca automática de CEP via ViaCEP), forma de pagamento e revisão final com aplicação de cupons.
- **Acompanhamento e Notificações**: linha do tempo com horários de cada mudança de status do pedido, estimativa de entrega e central de notificações na área do perfil.
- **Repetir Pedido**: recurso no histórico de pedidos que valida a disponibilidade atual dos itens e os reinsere no carrinho com um clique.

### Administrador (Funcionário da Confeitaria)
- **Painel Operacional Dedicado (`/painel/`)**: área administrativa exclusiva para colaboradores com permissão de equipe (`is_staff`).
- **Gestão de Produtos**: cadastro, edição e exclusão lógica (*soft delete*) de cupcakes para preservar o histórico de vendas, além de validação estrita de imagens (extensão, tamanho máximo de 5 MB e integridade via Pillow).
- **Gestão de Pedidos**: visualização filtrada por status, período e cliente, atualização dos estágios de preparo e envio, e cancelamento restrito aos pedidos em aberto ou em preparação com reposição automática de estoque.
- **Django Admin (`/admin/`)**: mantido para manutenção estrutural avançada e auditoria do banco de dados.

---

## Arquitetura e Tecnologias

### Stack Técnica
- **Linguagem e Framework**: Python 3 e Django 5.2.
- **Banco de Dados**: SQLite, sem dependência de serviços externos pesados.
- **Processamento de Imagens**: Pillow para geração e validação de arquivos de imagem.
- **Frontend**: HTML5 semântico, CSS3 puro e JavaScript Vanilla (sem React, Vue ou bundlers). Tipografia carregada via Google Fonts (Poppins e Nunito).
- **Testes Automatizados**: pytest e pytest-django.

### Correspondência MTV do Django com o MVC da Disciplina
Durante as aulas estudamos o padrão arquitetural MVC (Model-View-Controller). No Django, a nomenclatura difere ligeiramente mas preserva os mesmos princípios de separação de responsabilidades:
- **Model**: corresponde diretamente ao **Model** do MVC. Define as tabelas, campos, regras de integridade e relacionamentos no banco de dados através do ORM.
- **View do Django**: atua como o **Controller** do MVC. É responsável por receber a requisição HTTP, invocar os serviços adequados, coordenar a lógica e selecionar o template que formará a resposta.
- **Template**: representa a **View** (visão) do MVC. Cuida exclusivamente da estrutura visual e apresentação dos dados para o navegador, sem conter regras de negócio.

Para manter o projeto modular e fácil de testar, adotei uma **camada de serviços (`services/`)** em cada aplicação (`auth_service`, `busca_service`, `carrinho_service`, `frete_service`, `cupom_service`, `estoque_service`, `pagamento_service`, `pedido_service`). As views permanecem limpas e atuam apenas como coordenadoras de entrada e saída.

---

## Passo a Passo para Executar Localmente

### 1. Criar e ativar o ambiente virtual
No terminal do seu sistema operacional, dentro da pasta do projeto:

No Windows (PowerShell):
```text
python -m venv .venv
.venv\Scripts\Activate.ps1
```

No Linux ou macOS:
```text
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependências
```text
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente
Copie o arquivo de exemplo para criar seu arquivo local:
```text
cp .env.example .env
```
Os valores padrão pré-configurados no `.env.example` já permitem executar e testar a aplicação em ambiente de desenvolvimento local.

### 4. Executar as migrações
```text
python manage.py migrate
```

### 5. Popular o banco com dados de teste
Execute o comando customizado para carregar categorias, cupcakes ilustrados, tabela de frete, cupom ativo, contas de usuário e pedidos de demonstração:
```text
python manage.py popular_dados
```

### 6. Iniciar o servidor
```text
python manage.py runserver
```
Abra o navegador no endereço: `http://127.0.0.1:8000/`

---

## Credenciais de Teste

O comando de carga cria duas contas pré-configuradas:

- **Administrador**:
  - E-mail: `admin@cupcakesgourmet.com`
  - Senha: a que você escolher ao rodar o comando (`python manage.py popular_dados --senha-admin SuaSenhaForte1`) ou a variável `ADMIN_PASSWORD`. Se não informar nenhuma, o comando gera uma senha aleatória e mostra no final da execução, uma única vez.
  - Permissões: acesso total ao painel administrativo (`/painel/`) e ao Django admin (`/admin/`).

- **Cliente**:
  - E-mail: `cliente@teste.com`
  - Senha: `Cliente@123456`
  - Endereço cadastrado: Rua das Flores, 123, Centro, Medianeira/PR (CEP 85884-000).

- **Cupom Promocional**:
  - Código: `CUPCAKE10` (10% de desconto em pedidos a partir de R$ 30,00).

---

## Cartões de Teste (Simulação de Pagamento)

Para testar o fluxo de checkout sem transações financeiras reais, utilize os números abaixo:

- **Cartão Aprovado**: `4111 1111 1111 1111`
  - Validade: qualquer mês/ano no futuro (ex: 12/2028)
  - CVV: qualquer código de 3 dígitos (ex: 123)
  - Nome: qualquer nome (ex: Cliente Teste)

- **Cartão Recusado**: `4000 0000 0000 0002`
  - Simula a rejeição da transação pela operadora, exibindo a tela de pagamento recusado e liberando as reservas de estoque.

- **Validação de Luhn**: qualquer sequência de dígitos que não passe no cálculo matemático de Luhn gera erro imediato no formulário. Por segurança, o sistema grava no banco apenas os quatro últimos dígitos do cartão.

---

## Como Rodar a Suíte de Testes

Utilizei o `pytest` integrado ao Django através do pacote `pytest-django`:

```text
pytest
```

Para rodar com relatório detalhado de cada teste executado:
```text
pytest -v
```

A suíte abrange testes de unidade e de integração organizados por domínio:
- Autenticação e bloqueio de tentativas (`test_usuarios.py`)
- Catálogo, busca insensível a acentos e ordenação (`test_catalogo.py`)
- Carrinho e validação de estoque (`test_carrinho.py`)
- Frete e cupons (`test_frete_cupom.py`)
- Reserva de estoque e checkout (`test_estoque_checkout.py`)
- Pagamentos com Luhn, juros compostos e PIX (`test_pagamento_pedido.py`)
- Status do pedido e notificações (`test_status_notificacoes.py`)
- Histórico e repetir pedido (`test_historico.py`)
- Painel administrativo e cancelamento (`test_painel.py`)
- Telas de erro, rotas offline e carga idempotente (`test_erros_dados.py`)
- Regressões de problemas encontrados na revisão do código (`test_regressoes.py`)

---

## Decisões de Projeto

- **Pagamento e Notificações Simulados**: por se tratar de um trabalho acadêmico sem fins lucrativos, evitei custos ou chaves de APIs proprietárias. Os cálculos de validação (Luhn), parcelamento (com juros compostos de 2,5% ao mês a partir da quarta parcela) e geração de payload do PIX são totalmente reais no código, mas operam em ambiente controlado com avisos informativos em tela. As notificações aos clientes são gravadas no próprio banco de dados.
- **Modo Demonstração (`MODO_DEMO`)**: para possibilitar a avaliação das funcionalidades online sem exigir um serviço de envio de e-mails corporativo configurado, as páginas de cadastro e de recuperação de senha exibem diretamente na tela um aviso visual em azul com o link gerado. Em ambiente de produção com `MODO_DEMO=False`, o sistema utiliza o envio de e-mails tradicional.
- **Reserva Temporária de Estoque**: para proteger a confeitaria contra vendas simultâneas do mesmo produto em excesso de estoque, o início do checkout reserva os itens do carrinho por 10 minutos. Ao selecionar pagamento via PIX, essa reserva é prorrogada para 30 minutos (tempo de validade do código PIX). A checagem de expiração é feita sob demanda (*lazy*), sem a necessidade de processos em segundo plano rodando continuamente no servidor.
- **Frete Regional com ViaCEP**: a integração com a API pública do ViaCEP preenche os dados de endereço a partir do CEP informado. O cálculo do frete é baseado em uma tabela própria por estado (cobrindo PR, SC, RS, SP, RJ e MG). Pedidos cujo subtotal de produtos (após abatimento de cupom) ultrapassa R$ 150,00 recebem frete grátis automaticamente.
- **Soft Delete de Produtos**: a exclusão de cupcakes no painel administrativo altera o campo `ativo` para `False`, ocultando o item da vitrine e da busca, mas preservando o registro para garantir que o histórico de pedidos de clientes antigos nunca perca a integridade referencial.
- **Autenticação por Sessão**: adotei o modelo nativo de sessões e cookies seguros do Django, mais adequado e confiável para aplicações renderizadas no servidor do que mecanismos como JWT.

---

## O que Fica para uma Próxima Versão

- Integração com um gateway de pagamentos real em ambiente de produção (como Mercado Pago ou Pagar.me).
- Envio de notificações ativas por WhatsApp ou SMS avisando sobre o avanço de cada etapa de entrega.
- Integração dinâmica com transportadoras e Correios para cotação automatizada de frete em tempo real por peso e volume.
- Módulo de personalização de encomendas (escolha de mensagens em plaquinhas de chocolate e caixas de presente).

---

## Publicação no PythonAnywhere (plano gratuito)

O sistema publicado está em https://tiagotstanis.pythonanywhere.com. Foi assim que eu coloquei no ar:

1. Criei a conta gratuita (plano Beginner) em pythonanywhere.com e abri um terminal **Bash** em *Consoles*.
2. Baixei o projeto e conferi as versões de Python disponíveis:
   ```text
   git clone https://github.com/TiagoTStanis/cupcakes-gourmet.git
   cd cupcakes-gourmet
   ls /usr/bin/python3.*
   ```
3. Criei o ambiente virtual com o Python 3.13 (o mesmo em que desenvolvi e testei) e instalei as dependências:
   ```text
   mkvirtualenv cupcakes-venv --python=/usr/bin/python3.13
   pip install -r requirements.txt
   ```
4. Criei o arquivo `.env` na pasta do projeto, com uma chave secreta gerada na hora. Troque `seu-usuario` pelo seu nome de usuário do PythonAnywhere, em minúsculas:
   ```text
   SECRET_KEY=<resultado de: python -c "import secrets; print(secrets.token_urlsafe(50))">
   DEBUG=False
   ALLOWED_HOSTS=seu-usuario.pythonanywhere.com
   CSRF_TRUSTED_ORIGINS=https://seu-usuario.pythonanywhere.com
   MODO_DEMO=True
   ```
   Deixe `MODO_DEMO=True` enquanto as pessoas testam: sem servidor de e-mail, o link de ativação aparece na própria tela. O sistema lê esse `.env` sozinho, e recusa iniciar com `DEBUG=False` se a `SECRET_KEY` não for definida.
5. Criei o banco, os arquivos estáticos e os dados de exemplo:
   ```text
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py popular_dados
   ```
   No final, o `popular_dados` mostra a senha do administrador, gerada na hora e exibida uma única vez. Anote. Se preferir escolher a senha, use `--senha-admin SuaSenha` ou a variável `ADMIN_PASSWORD`.
6. Na aba **Web**, cliquei em *Add a new web app*, escolhi *Manual configuration* e **Python 3.13**. Depois preenchi:
   - **Source code** e **Working directory**: `/home/seu-usuario/cupcakes-gourmet`
   - **Virtualenv**: `/home/seu-usuario/.virtualenvs/cupcakes-venv`
   - **Static files**: `/static/` apontando para `/home/seu-usuario/cupcakes-gourmet/staticfiles` e `/media/` apontando para `/home/seu-usuario/cupcakes-gourmet/media`
   - **Force HTTPS**: ativado
   - **Arquivo WSGI** (link na seção *Code*): troquei todo o conteúdo por
     ```python
     import os
     import sys
     sys.path.insert(0, "/home/seu-usuario/cupcakes-gourmet")
     os.environ["DJANGO_SETTINGS_MODULE"] = "cupcakes_gourmet.settings"
     from django.core.wsgi import get_wsgi_application
     application = get_wsgi_application()
     ```
7. Cliquei no botão verde **Reload** e abri o endereço do site.

No plano gratuito, o site é desativado depois de um mês. É preciso entrar na aba **Web** uma vez por mês e clicar em *Run until 1 month from today*.
