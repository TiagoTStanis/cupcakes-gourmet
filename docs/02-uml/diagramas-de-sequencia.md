# Diagramas de sequência e fluxo de checkout

Este documento apresenta a modelagem dinâmica das principais operações do sistema **Cupcakes Gourmet** para o PITE II (Engenharia de Software, Cruzeiro do Sul). Foram elaborados três diagramas de sequência em Mermaid detalhando as interações entre os atores, templates/JavaScript, views, serviços de domínio e o banco de dados SQLite, além de um fluxograma com as decisões críticas do checkout.

---

## 1. Compra com cartão de crédito aprovado (do carrinho ao pedido pago)

Este diagrama representa o fluxo em que o cliente avança pelo checkout em 3 etapas, informa um cartão de crédito válido e obtém a confirmação imediata da compra com baixa física de estoque.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente
    participant Interface as Template / JS
    participant View as pedidos.views
    participant Servico as pedido_service / estoque_service
    participant BD as Banco de Dados (SQLite)

    Cliente->>Interface: Clica em "Finalizar Compra" no carrinho
    Interface->>View: GET /pedidos/checkout/
    View->>Servico: reservar_itens(usuario, itens_carrinho)
    Servico->>BD: Cria/atualiza ReservaEstoque (expira em 10 min)
    View-->>Interface: Renderiza Etapa 1: Seleção de Endereço (pedidos/endereco.html)

    Cliente->>Interface: Seleciona endereço e clica em "Continuar para Pagamento"
    Interface->>View: POST /pedidos/checkout/ (endereco_id)
    View->>Servico: calcular_frete(uf)
    View->>View: Salva endereco_id e frete na sessão
    View-->>Interface: Redireciona para /pedidos/checkout/pagamento/

    Interface->>View: GET /pedidos/checkout/pagamento/
    View-->>Interface: Renderiza Etapa 2: Escolha da Forma de Pagamento

    Cliente->>Interface: Seleciona "Cartão de Crédito" e clica em "Revisar Pedido"
    Interface->>View: POST /pedidos/checkout/pagamento/ (forma_pagamento='CARTAO')
    View->>View: Salva forma na sessão
    View-->>Interface: Redireciona para /pedidos/checkout/resumo/

    Interface->>View: GET /pedidos/checkout/resumo/
    View->>Servico: opcoes_parcelamento(total)
    View-->>Interface: Renderiza Etapa 3: Resumo, parcelamento e dados do cartão

    Cliente->>Interface: Preenche dados do cartão (4111...) e clica em "Confirmar Pedido"
    Interface->>View: POST /pedidos/checkout/confirmar/ (numero, validade, cvv, parcelas)
    View->>Servico: criar_pedido(usuario, carrinho, endereco, sessao, 'CARTAO', dados)
    
    activate Servico
    Servico->>Servico: estoque_service.garantir_reservas()
    Servico->>Servico: pagamento_service.processar_cartao() (valida Luhn e parcelas)
    Servico->>BD: Cria registro em Pedido e ItemPedido
    Servico->>BD: Registra uso de cupom em CupomUso (se aplicável)
    Servico->>Servico: alterar_status(pedido, 'PAGAMENTO_CONFIRMADO')
    Servico->>Servico: estoque_service.dar_baixa(pedido)
    Servico->>BD: Subtrai Produto.estoque e incrementa Produto.total_vendas
    Servico->>BD: Desativa ReservaEstoque do cliente
    Servico->>BD: Cria registro inicial em HistoricoStatus
    Servico->>BD: Cria Notificacao para o cliente
    Servico->>BD: Esvazia itens do Carrinho
    Servico->>View: Retorna instância do Pedido criado
    deactivate Servico

    View-->>Interface: Redireciona para /pedidos/pedido/<numero>/
    Interface->>View: GET /pedidos/pedido/<numero>/
    View-->>Interface: Renderiza tela de confirmação e linha do tempo (pedidos/confirmacao.html)
```

---

## 2. Compra com PIX (aguardando, reserva de 30 min, confirmação e expiração)

Este diagrama detalha o comportamento do pagamento via PIX, abrangendo a extensão da reserva para 30 minutos, o caminho de confirmação simulada e o caminho alternativo de cancelamento por expiração.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente
    participant Interface as Template / JS
    participant View as pedidos.views
    participant Servico as pedido_service / pagamento_service
    participant BD as Banco de Dados (SQLite)

    Cliente->>Interface: Na Etapa 2 escolhe "PIX" e clica em "Confirmar" na Etapa 3
    Interface->>View: POST /pedidos/checkout/confirmar/ (forma_pagamento='PIX')
    View->>Servico: criar_pedido(usuario, carrinho, endereco, sessao, 'PIX')
    
    activate Servico
    Servico->>Servico: pagamento_service.gerar_pix(numero, total) (expira em +30 min)
    Servico->>BD: Cria Pedido (status='AGUARDANDO_PAGAMENTO', pix_expira_em)
    Servico->>BD: Cria registros de ItemPedido
    Servico->>BD: Atualiza ReservaEstoque (estende validade para 30 min)
    Servico->>BD: Cria registro inicial em HistoricoStatus
    Servico->>BD: Esvazia itens do Carrinho
    Servico-->>View: Retorna Pedido criado
    deactivate Servico

    View-->>Interface: Redireciona para /pedidos/pedido/<numero>/
    Interface->>View: GET /pedidos/pedido/<numero>/
    View->>Servico: pagamento_service.desenhar_qr(codigo_pix)
    View-->>Interface: Renderiza tela do PIX (pedidos/pix.html) com QR Code SVG e código copia-e-cola

    alt Caminho de Sucesso: Cliente confirma pagamento antes de 30 min
        Cliente->>Interface: Clica em "Confirmar Pagamento (Simulação)"
        Interface->>View: POST /pedidos/pedido/<numero>/confirmar-pix/
        View->>Servico: confirmar_pix(pedido, usuario)
        Servico->>Servico: verificar_expiracao(pedido) (pix_expira_em > now)
        Servico->>Servico: alterar_status(pedido, 'PAGAMENTO_CONFIRMADO')
        Servico->>BD: estoque_service.dar_baixa(pedido) (baixa física do estoque)
        Servico->>BD: Desativa ReservaEstoque
        Servico->>BD: Cria HistoricoStatus e Notificacao
        View-->>Interface: Redireciona para /pedidos/pedido/<numero>/
        Interface-->>Cliente: Exibe pedido confirmado na linha do tempo de entrega
    else Caminho Alternativo: Prazo de 30 min expira sem pagamento
        Note over Cliente,BD: Transcorreram mais de 30 minutos
        Cliente->>Interface: Acessa /pedidos/pedido/<numero>/ ou clica em confirmar
        Interface->>View: GET ou POST
        View->>Servico: verificar_expiracao(pedido, usuario)
        Servico->>Servico: Detecta pix_expira_em <= timezone.now()
        Servico->>Servico: alterar_status(pedido, 'CANCELADO', motivo='PIX expirado')
        Servico->>BD: Desativa ReservaEstoque (libera unidades de volta ao catálogo)
        Servico->>BD: Registra cancelamento em HistoricoStatus e Notificacao
        View-->>Interface: Renderiza aviso de PIX expirado e pedido cancelado
    end
```

---

## 3. Cancelamento pelo administrador com reposição de estoque e notificação

Este diagrama mostra como o administrador da confeitaria atua no painel para cancelar um pedido em andamento, garantindo que o estoque seja reposto com segurança e que o cliente receba a notificação correspondente.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Administrador (Staff)
    participant PainelUI as Template do Painel
    participant View as painel.views
    participant Servico as pedido_service / estoque_service
    participant BD as Banco de Dados (SQLite)

    Admin->>PainelUI: Acessa detalhes do pedido (/painel/pedidos/<numero>/)
    PainelUI->>View: GET /painel/pedidos/<numero>/
    View->>BD: Carrega Pedido (status='EM_PREPARACAO', estoque_baixado=True)
    View-->>PainelUI: Exibe dados e botão "Cancelar Pedido" habilitado

    Admin->>PainelUI: Clica em "Cancelar Pedido" e confirma motivo
    PainelUI->>View: POST /painel/pedidos/<numero>/cancelar/
    View->>Servico: alterar_status(pedido, 'CANCELADO', motivo)

    activate Servico
    Servico->>Servico: Valida que status atual ('EM_PREPARACAO') permite cancelamento
    Servico->>Servico: Verifica que pedido.estoque_baixado == True
    
    Servico->>Servico: estoque_service.repor_estoque(pedido)
    Servico->>BD: Incrementa Produto.estoque (+quantidade de cada item)
    Servico->>BD: Decrementa Produto.total_vendas (-quantidade)
    Servico->>BD: Atualiza pedido.estoque_baixado = False
    
    Servico->>BD: Atualiza pedido.status = 'CANCELADO'
    Servico->>BD: Insere registro no HistoricoStatus ('CANCELADO')
    Servico->>BD: Cria Notificacao para o cliente ("Pedido cancelado: motivo")
    Servico-->>View: Retorna Pedido atualizado
    deactivate Servico

    View-->>PainelUI: Redireciona com mensagem de sucesso
    PainelUI-->>Admin: Exibe pedido atualizado como "Cancelado" e botão de cancelamento agora desabilitado
```

---

## 4. Fluxograma do checkout em 3 etapas e decisões de validação

O fluxograma abaixo detalha todas as etapas do processo de checkout, mapeando os desvios causados por reservas expiradas, indisponibilidade física de itens e recusa de pagamento simulado.

```mermaid
flowchart TD
    Inicio([Carrinho com itens]) --> IniciarCheckout[Cliente clica em Finalizar Compra]
    
    IniciarCheckout --> ValidaEstoque{Há estoque físico disponível para todos os itens?}
    ValidaEstoque -- Não --> AvisoSemEstoque[Emite aviso de produto esgotado e volta ao carrinho]
    ValidaEstoque -- Sim --> CriaReserva[Cria ReservaEstoque temporária de 10 minutos]
    
    CriaReserva --> Etapa1[Etapa 1: Seleção de Endereço]
    Etapa1 --> ValidaCEP{CEP informado pertence a UF atendida? PR, SC, RS, SP, RJ, MG}
    ValidaCEP -- Não --> ErroUF[Exibe erro: Infelizmente não entregamos neste endereço ainda]
    ErroUF --> Etapa1
    ValidaCEP -- Sim --> SalvaEndereco[Calcula frete pela tabela por UF e grava na sessão]
    
    SalvaEndereco --> Etapa2[Etapa 2: Forma de Pagamento]
    Etapa2 --> EscolheForma{Qual forma de pagamento foi escolhida?}
    
    EscolheForma -- Cartão de Crédito --> Etapa3Cartao[Etapa 3: Resumo com opções de parcelamento]
    EscolheForma -- PIX --> Etapa3PIX[Etapa 3: Resumo com valor à vista sem juros]
    
    Etapa3Cartao --> ConfirmaCartao[Cliente informa dados do cartão e confirma compra]
    ConfirmaCartao --> ChecaReservaCartao{A reserva de 10 min expirou antes da confirmação?}
    ChecaReservaCartao -- Sim e produto esgotou --> ErroReservaCartao[Libera reserva, avisa cliente e volta ao carrinho]
    ChecaReservaCartao -- Não ou há estoque --> ValidaLuhn{Cartão válido pelo algoritmo de Luhn?}
    
    ValidaLuhn -- Não --> ErroFormCartao[Exibe erros nos campos e mantém na Etapa 2]
    ValidaLuhn -- Sim --> ChecaSimulacao{Cartão é 4000 0000 0000 0002 de teste recusado?}
    
    ChecaSimulacao -- Sim --> TelaRecusado[Libera reservas e exibe tela: Pagamento Recusado]
    ChecaSimulacao -- Não --> CriaPedidoPago[Cria Pedido como PAGAMENTO_CONFIRMADO, dá baixa definitiva no estoque, esvazia carrinho]
    CriaPedidoPago --> FimCartao([Tela de Confirmação e Rastreamento])
    
    Etapa3PIX --> ConfirmaPIX[Cliente clica em Confirmar Pedido]
    ConfirmaPIX --> CriaPedidoPIX[Cria Pedido AGUARDANDO_PAGAMENTO, estende reserva para 30 min, esvazia carrinho]
    CriaPedidoPIX --> TelaPIX[Exibe tela do PIX com QR Code SVG e código copia-e-cola]
    
    TelaPIX --> AcaoPIX{Cliente confirma pagamento na simulação dentro dos 30 minutos?}
    AcaoPIX -- Não / Expirou --> CancelaPIX[Status vira CANCELADO, libera reserva de estoque sem baixar saldo físico]
    CancelaPIX --> FimPIXExpirado([Tela de PIX Expirado])
    AcaoPIX -- Sim --> BaixaPIX[Status vira PAGAMENTO_CONFIRMADO, baixa estoque físico definitivo]
    BaixaPIX --> FimPIX([Tela de Confirmação e Rastreamento])
```
