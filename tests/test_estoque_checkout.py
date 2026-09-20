from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from carrinho.services import carrinho_service
from pedidos.models import ItemPedido, Pedido, ReservaEstoque
from pedidos.services import estoque_service
from usuarios.models import Endereco


pytestmark = pytest.mark.django_db


@pytest.fixture
def endereco(usuario_cliente):
    return Endereco.objects.create(
        usuario=usuario_cliente, cep="85801-000", logradouro="Rua Paraná", numero="120",
        bairro="Centro", cidade="Cascavel", uf="PR",
    )


@pytest.fixture
def pedido(usuario_cliente, produtos_com_estoque):
    produto = produtos_com_estoque[0]
    pedido = Pedido.objects.create(
        numero="TESTE-001", usuario=usuario_cliente, endereco_entrega="Rua Paraná, 120, Cascavel/PR",
        subtotal=Decimal("25.00"), valor_frete=Decimal("10.00"),
        valor_total=Decimal("35.00"), forma_pagamento="CARTAO",
    )
    ItemPedido.objects.create(
        pedido=pedido, produto=produto, nome_produto=produto.nome,
        preco_unitario=produto.preco, quantidade=2, subtotal=Decimal("25.00"),
    )
    return pedido


def iniciar_checkout(client, usuario, endereco):
    client.force_login(usuario)
    return client.post(reverse("pedidos:checkout_endereco"), {"endereco_id": endereco.pk})


def test_reserva_reduz_disponivel_para_outro_usuario(usuario_cliente, usuario_admin, carrinho_com_itens):
    item = carrinho_com_itens.itens.first()
    estoque_service.reservar_itens(usuario_cliente, carrinho_com_itens.itens.all())
    assert estoque_service.estoque_disponivel(item.produto, usuario_admin) == item.produto.estoque - item.quantidade
    assert estoque_service.estoque_disponivel(item.produto, usuario_cliente) == item.produto.estoque


def test_reserva_expirada_libera_unidades(usuario_cliente, carrinho_com_itens):
    item = carrinho_com_itens.itens.first()
    estoque_service.reservar_itens(usuario_cliente, carrinho_com_itens.itens.all())
    ReservaEstoque.objects.update(expira_em=timezone.now() - timedelta(seconds=1))
    assert estoque_service.estoque_disponivel(item.produto) == item.produto.estoque
    assert not ReservaEstoque.objects.filter(ativa=True).exists()


def test_renovar_reserva_atualiza_prazo_sem_duplicar(usuario_cliente, carrinho_com_itens):
    estoque_service.reservar_itens(usuario_cliente, carrinho_com_itens.itens.all())
    ids = list(ReservaEstoque.objects.values_list("pk", flat=True))
    ReservaEstoque.objects.update(expira_em=timezone.now() + timedelta(minutes=1))
    antes = timezone.now()
    expira_em = estoque_service.reservar_itens(usuario_cliente, carrinho_com_itens.itens.all())
    assert list(ReservaEstoque.objects.values_list("pk", flat=True)) == ids
    assert antes + timedelta(minutes=10) <= expira_em <= timezone.now() + timedelta(minutes=10)


def test_reserva_insuficiente_desfaz_toda_operacao(usuario_cliente, carrinho_com_itens):
    itens = list(carrinho_com_itens.itens.order_by("produto_id"))
    itens[-1].produto.estoque = 0
    itens[-1].produto.save()
    with pytest.raises(estoque_service.ErroEstoque):
        estoque_service.reservar_itens(usuario_cliente, itens)
    assert not ReservaEstoque.objects.exists()


def test_dar_baixa_e_idempotente_e_consome_reservas(pedido, carrinho_com_itens):
    produto = pedido.itens.get().produto
    estoque, vendas = produto.estoque, produto.total_vendas
    estoque_service.reservar_itens(pedido.usuario, carrinho_com_itens.itens.all())
    copia = Pedido.objects.get(pk=pedido.pk)
    estoque_service.dar_baixa(pedido)
    estoque_service.dar_baixa(copia)
    produto.refresh_from_db()
    pedido.refresh_from_db()
    assert (produto.estoque, produto.total_vendas) == (estoque - 2, vendas + 2)
    assert pedido.estoque_baixado
    assert not ReservaEstoque.objects.filter(usuario=pedido.usuario, produto=produto, ativa=True).exists()


def test_baixa_respeita_reserva_de_outro_usuario(pedido, usuario_admin):
    produto = pedido.itens.get().produto
    ReservaEstoque.objects.create(
        usuario=usuario_admin, produto=produto, quantidade=produto.estoque,
        expira_em=timezone.now() + timedelta(minutes=10),
    )
    with pytest.raises(estoque_service.ErroEstoque):
        estoque_service.dar_baixa(pedido)
    pedido.refresh_from_db()
    assert not pedido.estoque_baixado


def test_repor_so_uma_vez_e_somente_apos_baixa(pedido):
    produto = pedido.itens.get().produto
    estoque, vendas = produto.estoque, produto.total_vendas
    estoque_service.repor_estoque(pedido)
    produto.refresh_from_db()
    assert produto.estoque == estoque
    estoque_service.dar_baixa(pedido)
    copia = Pedido.objects.get(pk=pedido.pk)
    estoque_service.repor_estoque(pedido)
    estoque_service.repor_estoque(copia)
    produto.refresh_from_db()
    pedido.refresh_from_db()
    assert (produto.estoque, produto.total_vendas) == (estoque, vendas)
    assert not pedido.estoque_baixado


def test_carrinho_respeita_reservas_alheias(usuario_cliente, usuario_admin, produtos_com_estoque):
    produto = produtos_com_estoque[1]
    carrinho = carrinho_service.obter_carrinho(usuario_cliente)
    carrinho_service.adicionar(carrinho, produto, 7)
    estoque_service.reservar_itens(usuario_cliente, carrinho.itens.all())
    outro = carrinho_service.obter_carrinho(usuario_admin)
    with pytest.raises(carrinho_service.ErroCarrinho, match="1 unidades"):
        carrinho_service.adicionar(outro, produto, 2)
    with pytest.raises(carrinho_service.ErroCarrinho):
        carrinho_service.alterar_quantidade(outro, produto, 2)
    carrinho_service.alterar_quantidade(carrinho, produto, 8)
    assert not ReservaEstoque.objects.filter(usuario=usuario_cliente, ativa=True).exists()


@pytest.mark.parametrize("rota", ["checkout_endereco", "checkout_pagamento", "checkout_resumo", "checkout_confirmar"])
def test_checkout_exige_login(client, rota):
    resposta = client.post(reverse("pedidos:" + rota)) if rota == "checkout_confirmar" else client.get(reverse("pedidos:" + rota))
    assert resposta.status_code == 302
    assert resposta.url.startswith(reverse("usuarios:login"))


@pytest.mark.parametrize("rota", ["checkout_endereco", "checkout_pagamento", "checkout_resumo", "checkout_confirmar"])
def test_checkout_vazio_volta_ao_carrinho(client, usuario_cliente, rota):
    client.force_login(usuario_cliente)
    resposta = client.post(reverse("pedidos:" + rota), follow=True) if rota == "checkout_confirmar" else client.get(reverse("pedidos:" + rota), follow=True)
    assert resposta.redirect_chain[0][0] == reverse("carrinho:detalhe")
    assert "Seu carrinho está vazio" in resposta.content.decode()


def test_item_esgotado_entre_carrinho_e_checkout_avisa(client, usuario_cliente, carrinho_com_itens):
    produto = carrinho_com_itens.itens.first().produto
    produto.estoque = 0
    produto.save()
    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:checkout_endereco"), follow=True)
    assert resposta.redirect_chain[0][0] == reverse("carrinho:detalhe")
    assert "Um dos itens ficou indisponível. Revise seu carrinho." in resposta.content.decode()


def test_uf_fora_da_tabela_bloqueia_endereco(client, usuario_cliente, carrinho_com_itens, endereco, tabela_frete):
    endereco.uf = "AC"
    endereco.save()
    resposta = iniciar_checkout(client, usuario_cliente, endereco)
    assert resposta.status_code == 200
    assert "Infelizmente não entregamos neste endereço ainda." in resposta.content.decode()
    assert "checkout_endereco_id" not in client.session


def test_resumo_confere_total_com_cupom_e_frete(client, usuario_cliente, carrinho_com_itens, endereco, tabela_frete, cupom_valido):
    iniciar_checkout(client, usuario_cliente, endereco)
    sessao = client.session
    sessao["cupom_codigo"] = cupom_valido.codigo
    sessao.save()
    resposta = client.post(reverse("pedidos:checkout_pagamento"), {"forma_pagamento": "PIX"}, follow=True)
    resumo = resposta.context["resumo"]
    assert resumo["subtotal"] == Decimal("36.00")
    assert resumo["desconto"] == Decimal("3.60")
    from pedidos.models import TabelaFreteUF
    assert resumo["frete"] == TabelaFreteUF.objects.get(uf="PR").valor
    assert resumo["total"] == Decimal("32.40") + resumo["frete"]
    assert "Ambiente de demonstração: pagamento simulado" in resposta.content.decode()
    assert "data-expira-em" in resposta.content.decode()
    assert not Pedido.objects.exists()


def test_usuario_so_ve_e_usa_endereco_proprio(client, usuario_cliente, usuario_admin, carrinho_com_itens, endereco, tabela_frete):
    alheio = Endereco.objects.create(
        usuario=usuario_admin, cep="85801-000", logradouro="Rua Reservada", numero="999",
        bairro="Centro", cidade="Cascavel", uf="PR",
    )
    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:checkout_endereco"))
    assert endereco.logradouro in resposta.content.decode()
    assert alheio.logradouro not in resposta.content.decode()
    resposta = client.post(reverse("pedidos:checkout_endereco"), {"endereco_id": alheio.pk})
    assert resposta.status_code == 200
    assert "checkout_endereco_id" not in client.session
    sessao = client.session
    sessao["checkout_endereco_id"] = alheio.pk
    sessao["checkout_forma_pagamento"] = "PIX"
    sessao.save()
    resposta = client.get(reverse("pedidos:checkout_resumo"))
    assert resposta.url == reverse("pedidos:checkout_endereco")


def test_cadastra_endereco_no_checkout(client, usuario_cliente, carrinho_com_itens, tabela_frete):
    client.force_login(usuario_cliente)
    resposta = client.post(reverse("pedidos:checkout_endereco"), {
        "endereco_id": "novo", "cep": "85801-000", "logradouro": "Rua Paraná", "numero": "120",
        "bairro": "Centro", "cidade": "Cascavel", "uf": "PR",
    })
    assert resposta.url == reverse("pedidos:checkout_pagamento")
    assert usuario_cliente.enderecos.get().pk == client.session["checkout_endereco_id"]


def test_reserva_expirada_sem_estoque_volta_ao_carrinho(client, usuario_cliente, usuario_admin, carrinho_com_itens, endereco, tabela_frete):
    iniciar_checkout(client, usuario_cliente, endereco)
    client.post(reverse("pedidos:checkout_pagamento"), {"forma_pagamento": "CARTAO"})
    ReservaEstoque.objects.update(expira_em=timezone.now() - timedelta(seconds=1))
    produto = carrinho_com_itens.itens.first().produto
    ReservaEstoque.objects.create(
        usuario=usuario_admin, produto=produto, quantidade=produto.estoque,
        expira_em=timezone.now() + timedelta(minutes=10),
    )
    resposta = client.post(reverse("pedidos:checkout_confirmar"), follow=True)
    assert resposta.redirect_chain[0][0] == reverse("carrinho:detalhe")
    assert "Um dos itens ficou indisponível" in resposta.content.decode()
    assert not Pedido.objects.exists()


def test_confirmacao_sem_dados_do_cartao_nao_cria_pedido_nem_baixa_estoque(client, usuario_cliente, carrinho_com_itens, endereco, tabela_frete):
    iniciar_checkout(client, usuario_cliente, endereco)
    reserva = ReservaEstoque.objects.first()
    expira_em = reserva.expira_em
    estoques = {item.produto_id: item.produto.estoque for item in carrinho_com_itens.itens.select_related("produto")}
    client.post(reverse("pedidos:checkout_pagamento"), {"forma_pagamento": "CARTAO"})
    resposta = client.post(reverse("pedidos:checkout_confirmar"))
    assert resposta.status_code == 200
    assert set(resposta.context["erros"]) == {"numero", "validade", "cvv", "nome"}
    assert "Informe um número de cartão válido." in resposta.content.decode()
    assert not Pedido.objects.exists()
    reserva.refresh_from_db()
    assert reserva.expira_em == expira_em
    assert {item.produto_id: item.produto.estoque for item in carrinho_com_itens.itens.select_related("produto")} == estoques


def test_etapas_nao_aceitam_pular_endereco_ou_pagamento(client, usuario_cliente, carrinho_com_itens, endereco, tabela_frete):
    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:checkout_resumo"))
    assert resposta.url == reverse("pedidos:checkout_endereco")
    iniciar_checkout(client, usuario_cliente, endereco)
    resposta = client.get(reverse("pedidos:checkout_resumo"))
    assert resposta.url == reverse("pedidos:checkout_pagamento")
    resposta = client.post(reverse("pedidos:checkout_pagamento"), {"forma_pagamento": "DINHEIRO"})
    assert resposta.status_code == 200
    assert "checkout_forma_pagamento" not in client.session
