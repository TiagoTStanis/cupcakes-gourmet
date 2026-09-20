# Manual de uso do sistema

Este manual foi elaborado para orientar os usuários do sistema **Cupcakes Gourmet**, abrangendo tanto os clientes da confeitaria quanto os colaboradores responsáveis pela operação dos pedidos no painel administrativo. O sistema foi desenvolvido para a disciplina PITE II (Engenharia de Software, Cruzeiro do Sul).

---

## 1. Guia do cliente

### Criar uma conta e ativar o cadastro

1. Acesse o menu inferior e clique na aba **Perfil**, ou acesse o link de login e escolha **Criar conta** (`/usuarios/cadastro/`).
2. Preencha seu nome completo, e-mail, telefone (opcional) e defina sua senha. A senha exige no mínimo 8 caracteres, contendo pelo menos uma letra maiúscula e um número. O indicador colorido abaixo do campo mostrará a força da senha em tempo real.
3. Clique no botão **Cadastrar**.
4. **Modo Demonstração Acadêmica**: como o projeto está configurado com `MODO_DEMO=True` para fins de avaliação sem necessidade de servidor SMTP real, um aviso azul será exibido no topo da página contendo o link direto de ativação. Basta clicar nele para ativar sua conta na hora. Caso estivesse em ambiente de produção tradicional, o link seria enviado para a sua caixa de entrada de e-mail.
5. Na tela de ativação, clique em **Confirmar Ativação** para liberar seu acesso.

### Entrar no sistema e recuperar a senha

- **Entrar**: na tela de login (`/usuarios/login/`), digite seu e-mail cadastrado e sua senha. Se você estava navegando em um produto e tentou adicioná-lo ao carrinho antes de logar, o sistema o levará de volta para o mesmo produto após a autenticação.
- **Recuperar senha**: se esqueceu sua credencial, clique em "Esqueci minha senha" na tela de login (`/usuarios/esqueci-senha/`) e digite seu e-mail. Em modo de demonstração, o link de redefinição aparecerá em destaque na caixa azul da tela. O token gerado possui uso único e expira em exatamente 60 minutos.

### Encontrar cupcakes na vitrine e na busca

- **Navegação por categorias**: na tela inicial (`/` ou `/inicio/`), utilize os botões em formato de cápsula (chips) para filtrar os produtos por "Clássicos", "Veganos" ou "Temáticos".
- **Ordenação**: utilize o seletor no topo da listagem para organizar os cupcakes por mais vendidos (popularidade), menor preço ou maior preço.
- **Busca rápida**: clique na aba **Busca** no menu inferior (`/busca/`). Digite qualquer parte do nome do produto. O sistema conta com pesquisa instantânea e normalização de texto, o que significa que buscar por "limao" ou "Limão" encontrará o Cupcake de Limão Siciliano da mesma forma.

### Consultar detalhes da receita e alergênicos

1. Clique sobre o card do cupcake desejado para abrir a página de detalhes (`/produto/<slug>/`).
2. Leia a lista completa de ingredientes.
3. Verifique o **banner amarelo de alergênicos**: se você possui restrições alimentares (como intolerância a lactose ou alergia a glúten e ovos), confira atentamente os alertas destacados antes de comprar.
4. Se o produto estiver com estoque zerado no momento, o botão de compra exibirá o texto **Indisponível** e ficará desabilitado para evitar pedidos que não possam ser atendidos.

### Montar o carrinho de compras

1. Na tela do cupcake, ajuste a quantidade desejada através dos botões `-` e `+` e clique em **Adicionar ao Carrinho**.
2. No carrinho (`/carrinho/`), você pode:
   - Aumentar ou diminuir unidades de cada item (o limite é de 10 unidades por sabor).
   - Remover itens clicando no botão "Remover".
   - Os valores de subtotal do item e total geral são recalculados instantaneamente sem recarregar a tela.
3. Seus itens permanecem salvos em sua conta por até 24 horas a partir da última alteração.

### Calcular frete e aplicar cupom de desconto

1. No carrinho, informe seu CEP no campo correspondente e clique em **Calcular**. O sistema busca a localidade via ViaCEP e aplica o valor e o prazo correspondente à tabela do seu estado (PR, SC, RS, SP, RJ ou MG).
2. Para aplicar um desconto, insira o código **`CUPCAKE10`** no campo de cupom e clique em **Aplicar Cupom**. Este cupom concede 10% de abatimento sobre os produtos em compras a partir de R$ 30,00. O desconto incide exclusivamente sobre o valor dos cupcakes, nunca sobre a taxa de frete.
3. **Regra de Frete Grátis**: se o valor dos seus cupcakes (já com o desconto do cupom subtraído) for superior a R$ 150,00, o frete passa automaticamente para R$ 0,00 com a indicação "Frete Grátis".

### Finalizar o pedido (Checkout em 3 etapas)

1. No carrinho, clique no botão **Finalizar Compra**. Ao clicar, o sistema cria uma **reserva temporária de estoque de 10 minutos** para garantir que ninguém compre seus cupcakes enquanto você digita os dados.
2. **Etapa 1 - Endereço** (`/pedidos/checkout/`): selecione um de seus endereços cadastrados ou marque "Cadastrar novo endereço" e digite os dados. Clique em **Continuar para Pagamento**.
3. **Etapa 2 - Forma de Pagamento** (`/pedidos/checkout/pagamento/`): escolha entre "Cartão de Crédito" ou "PIX" e clique em **Revisar Pedido**.
4. **Etapa 3 - Revisão e Confirmação** (`/pedidos/checkout/resumo/`):
   - **Se escolheu Cartão de Crédito**: selecione a quantidade de parcelas desejada (de 1x até 3x sem juros; de 4x até 12x com acréscimo de juros de 2,5% a.m.), preencha o número do cartão, nome impresso, validade futura (MM/AA) e código de segurança CVV (3 dígitos). Clique em **Confirmar Pedido**.
   - **Se escolheu PIX**: confira o valor à vista e clique em **Confirmar Pedido**.

### Concluir o pagamento por PIX simulado

1. Ao confirmar um pedido com PIX, você é direcionado para a tela com o QR Code e o código "Copia e Cola" (`/pedidos/pedido/<numero>/`).
2. A reserva dos seus cupcakes é prorrogada para **30 minutos**, correspondendo ao tempo limite do PIX.
3. Para validar o fluxo durante os testes acadêmicos, basta clicar no botão **Confirmar Pagamento (Simulação)** na parte inferior da tela. O status do pedido mudará na hora para "Pagamento Confirmado" e a baixa definitiva do estoque será realizada.

### Acompanhar o pedido, ver notificações e histórico

- **Linha do tempo**: na tela do pedido (`/pedidos/pedido/<numero>/`), acompanhe as etapas de preparo em tempo real: *Aguardando Pagamento* -> *Pagamento Confirmado* -> *Em Preparação* -> *Saiu para Entrega* -> *Entregue*. Cada etapa exibe a data e a hora em que foi concluída.
- **Central de notificações**: clique no ícone de sino no canto superior direito do cabeçalho (`/pedidos/notificacoes/`). Você verá avisos automáticos enviados a cada avanço no status da sua encomenda.
- **Histórico e Repetir Pedido**: acesse a aba **Pedidos** no menu inferior (`/pedidos/`). Você verá todas as suas compras anteriores. Para pedir os mesmos doces novamente, clique no botão **Repetir Pedido**: o sistema verificará se os itens ainda existem e se há estoque suficiente, inserindo-os automaticamente no seu carrinho atual.

---

## 2. Guia do administrador da confeitaria

O acesso administrativo destina-se a colaboradores da confeitaria que possuam a permissão de equipe (`is_staff=True`).

### Acessar o painel operacional

1. Faça login com sua conta administrativa.
2. Um link com o texto **Painel** aparecerá no cabeçalho do site, ao lado do sino de notificações. Você também pode acessar diretamente pela URL `/painel/`.
3. A página inicial do painel (`/painel/`) apresenta um resumo das operações: quantidade total de pedidos, produtos ativos, lista de pedidos distribuídos por status e um card de destaque em amarelo indicando doces com estoque baixo (5 unidades ou menos).

### Gerenciar produtos (Cadastro, edição e desativação)

1. No menu do painel, clique em **Produtos** (`/painel/produtos/`).
2. **Cadastrar novo cupcake**: clique em **Novo Cupcake** (`/painel/produtos/novo/`), informe o nome da receita, selecione a categoria, descreva o doce, informe os ingredientes e os alergênicos obrigatórios, defina o preço de venda, a quantidade de estoque inicial e faça o upload de uma foto (extensões permitidas: JPG, JPEG ou PNG, com tamanho máximo de 5 MB). O sistema valida a integridade do arquivo através da biblioteca Pillow.
3. **Editar produto**: localize o cupcake na lista e clique em **Editar**. Você pode alterar preço, descrição ou repor unidades de estoque.
4. **Desativar produto (Soft Delete)**: se um sabor sair de linha temporariamente, clique em **Desativar**. O sistema realiza a exclusão lógica, ocultando o item da vitrine pública imediatamente, mas sem remover a linha do banco de dados para não corromper o histórico dos pedidos antigos dos clientes. Caso o sabor retorne, basta clicar em **Reativar**.

### Gerenciar categorias de produtos

1. Acesse **Categorias** no painel (`/painel/categorias/`).
2. Visualize as categorias ativas e a contagem de produtos associados a cada uma.
3. Você pode cadastrar novas categorias ou desativar categorias existentes quando necessário.

### Acompanhar, avançar e cancelar pedidos

1. Acesse **Pedidos** no painel (`/painel/pedidos/`).
2. Utilize os filtros superiores para listar encomendas por status (ex: listar somente os que estão "Em preparação"), cliente ou data.
3. Clique em **Ver Detalhes** para abrir a ficha operacional do pedido (`/painel/pedidos/<numero>/`).
4. **Avançar o status**: à medida que a cozinha produz os doces e o entregador sai para a rota, clique no botão **Avançar Status**:
   - De *Pagamento Confirmado* para *Em Preparação*.
   - De *Em Preparação* para *Saiu para Entrega*.
   - De *Saiu para Entrega* para *Entregue*.
   O cliente recebe uma notificação instantânea em sua conta a cada clique.
5. **Cancelar pedido**:
   - O botão de cancelamento só está disponível caso o pedido esteja no estágio **Aguardando Pagamento** ou **Em Preparação**.
   - Ao cancelar um pedido em preparação, o sistema executa atomicamente a **reposição de estoque físico**, devolvendo cada uma das unidades ao saldo do produto no catálogo e ajustando o total de vendas.
   - Caso o pedido já esteja em rota externa (*Saiu para Entrega*) ou já tenha sido *Entregue*, o botão de cancelamento fica bloqueado na interface para evitar divergências de estoque físico.

---

## 3. Dados e credenciais pré-configuradas para testes

Para facilitar a validação de todas as funcionalidades descritas, utilize as contas e parâmetros de demonstração carregados pelo comando `python manage.py popular_dados`:

### Contas de usuário

- **Administrador (Staff)**:
  - E-mail: `admin@cupcakesgourmet.com`
  - Senha: a definida na carga de dados (`popular_dados --senha-admin` ou `ADMIN_PASSWORD`; sem isso, o comando gera uma e mostra no final).
  - Acesso: vitrine pública, painel administrativo `/painel/` e Django admin `/admin/`.
- **Cliente comum (com e-mail já confirmado)**:
  - E-mail: `cliente@teste.com`
  - Senha: `Cliente@123456`
  - Endereço cadastrado: Rua das Flores, 123, Centro, Medianeira/PR (CEP 85884-000).

### Cupom promocional

- **Código**: `CUPCAKE10`
- **Regra**: 10% de desconto no subtotal dos produtos em compras a partir de R$ 30,00. Uso único por cliente.

### Cartões para simulação de pagamento

- **Cartão de Teste Aprovado**:
  - Número: `4111 1111 1111 1111`
  - Validade: qualquer mês/ano futuro (ex: `12/2028`)
  - CVV: qualquer sequência de 3 dígitos (ex: `123`)
  - Nome impresso: qualquer nome
- **Cartão de Teste Recusado**:
  - Número: `4000 0000 0000 0002`
  - Simula a rejeição da cobrança pela operadora, direcionando para a tela de pagamento recusado e liberando o estoque reservado.
- **Validação de formato**: qualquer número que não passe no cálculo do algoritmo de Luhn (ex: números com dígitos repetidos como `1111 1111 1111 1111` ou sequências aleatórias inválidas) será bloqueado com mensagem de erro antes do envio.

---

## 4. Problemas comuns e o que fazer

### 1. Conta bloqueada por 15 minutos
- **O que aconteceu**: foram inseridas 3 senhas incorretas consecutivas para a mesma conta de e-mail. Por segurança contra invasões por força bruta, o sistema trava o login desse usuário por exatamente 15 minutos.
- **O que fazer**: aguarde o término do intervalo de 15 minutos e tente novamente com a senha correta, ou utilize o fluxo de "Esqueci minha senha" para criar uma nova senha através do token de redefinição.

### 2. Reserva de estoque expirada durante o checkout
- **O que aconteceu**: ao entrar na etapa de endereço do checkout, seus itens recebem uma reserva garantida de 10 minutos. Se você demorou mais do que esse tempo para preencher os dados e, nesse intervalo, outro cliente comprou as últimas unidades daquele doce, o estoque esgotou.
- **O que fazer**: o sistema exibirá a mensagem *"Um dos itens ficou indisponível. Revise seu carrinho."* e redirecionará você para o carrinho. Basta ajustar as quantidades ou escolher outro sabor disponível para prosseguir.

### 3. Código PIX expirado
- **O que aconteceu**: o código PIX emitido possui prazo limite de 30 minutos. Se o pagamento não for confirmado dentro desse período, o sistema cancela a cobrança automaticamente e devolve os doces para a vitrine para evitar bloqueio indefinido de estoque.
- **O que fazer**: ao tentar confirmar um PIX vencido, a tela informará que o prazo encerrou. Acesse a aba de pedidos ou seu carrinho e inicie uma nova compra.

### 4. CEP inválido ou endereço fora da área de entrega
- **O que aconteceu**: ao digitar o CEP, você recebeu a mensagem *"CEP inválido"* ou *"Infelizmente não entregamos neste endereço ainda"*.
- **O que fazer**:
  - Certifique-se de preencher os 8 dígitos numéricos do CEP sem letras.
  - A confeitaria atende entregas regionais nos estados do Paraná (PR), Santa Catarina (SC), Rio Grande do Sul (RS), São Paulo (SP), Rio de Janeiro (RJ) e Minas Gerais (MG). Caso o CEP informado pertença a outra unidade federativa, utilize um endereço dentro da área coberta para testar a entrega.
