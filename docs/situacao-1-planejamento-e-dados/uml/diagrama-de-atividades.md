# Diagramas de atividades

Fiz três diagramas de atividades para os fluxos em que mais existem decisões: cadastro com ativação, compra e cancelamento pelo administrador. Cada raia mostra quem executa a ação. As regras são as mesmas que estão nos serviços do sistema.

## 1. Cadastro e ativação da conta

```mermaid
flowchart TD
    subgraph Cliente
        A1([Abre a tela de cadastro]) --> A2[Preenche nome, e-mail e senha]
        A3[Abre o link de ativação]
        A4([Entra no sistema])
    end
    subgraph Sistema
        B1{Dados válidos?}
        B2[Mostra o erro no campo]
        B3[Cria a conta e gera o token de ativação]
        B4{Modo demonstração?}
        B5[Mostra o link em um aviso azul na tela]
        B6[Envia o link por e-mail]
        B7[Marca o e-mail como confirmado]
    end
    A2 --> B1
    B1 -- Não --> B2 --> A2
    B1 -- Sim --> B3 --> B4
    B4 -- Sim --> B5 --> A3
    B4 -- Não --> B6 --> A3
    A3 --> B7 --> A4
```

## 2. Compra com cartão ou PIX

```mermaid
flowchart TD
    subgraph Cliente
        C1([Adiciona cupcakes ao carrinho]) --> C2[Informa o CEP e, se quiser, o cupom]
        C2 --> C3[Inicia o checkout e escolhe o endereço]
        C3 --> C4[Escolhe cartão ou PIX e confirma]
        C9[Confirma o PIX na simulação]
    end
    subgraph Sistema
        S1[Reserva o estoque por 10 minutos]
        S2{Itens ainda disponíveis?}
        S3[Avisa que um item esgotou e volta ao carrinho]
        S4{Forma de pagamento}
        S5{Cartão aprovado?}
        S6[Mostra a tela de pagamento recusado]
        S7[Cria o pedido pago, baixa o estoque e notifica]
        S8[Cria o pedido aguardando pagamento e estende a reserva para 30 minutos]
        S10{Dentro dos 30 minutos?}
        S11[Confirma o pagamento, baixa o estoque e notifica]
        S12[Cancela o pedido e libera a reserva]
        S13([Fim: pedido acompanhado na linha do tempo])
    end
    C3 --> S1 --> S2
    S2 -- Não --> S3
    S2 -- Sim --> C4
    C4 --> S4
    S4 -- Cartão --> S5
    S5 -- Não --> S6
    S5 -- Sim --> S7 --> S13
    S4 -- PIX --> S8 --> C9 --> S10
    S10 -- Sim --> S11 --> S13
    S10 -- Não --> S12
```

## 3. Cancelamento de pedido pelo administrador

```mermaid
flowchart TD
    subgraph Administrador
        D1([Abre o pedido no painel]) --> D2[Clica em cancelar e informa o motivo]
    end
    subgraph Sistema
        E1{Status é Aguardando pagamento ou Em preparação?}
        E2[Bloqueia a ação e explica o motivo]
        E3{O estoque já foi baixado?}
        E4[Repõe o estoque uma única vez]
        E5[Libera as reservas e desfaz o uso do cupom]
        E6[Muda o status para Cancelado e grava o histórico]
        E7[Notifica o cliente com o motivo]
        E8([Fim])
    end
    D2 --> E1
    E1 -- Não --> E2 --> E8
    E1 -- Sim --> E3
    E3 -- Sim --> E4 --> E6
    E3 -- Não --> E5 --> E6
    E6 --> E7 --> E8
```
