import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from xml.etree import ElementTree

import pytest
from django.urls import reverse
from django.utils import timezone

from carrinho.services import carrinho_service
from pedidos.models import CupomUso, HistoricoStatus, Pedido, ReservaEstoque
from pedidos.services import estoque_service, pagamento_service, pedido_service
from usuarios.models import Endereco


pytestmark = pytest.mark.django_db


@pytest.fixture
def dados_cartao():
    return {"numero": "4111 1111 1111 1111", "validade": "12/99", "cvv": "123", "nome": "Marina Souza", "parcelas": "1"}


@pytest.fixture
def compra(client, usuario_cliente, carrinho_com_itens, tabela_frete):
    endereco = Endereco.objects.create(
        usuario=usuario_cliente, cep="85801-000", logradouro="Rua Paraná", numero="120",
        bairro="Centro", cidade="Cascavel", uf="PR",
    )
    client.force_login(usuario_cliente)
    client.post(reverse("pedidos:checkout_endereco"), {"endereco_id": endereco.pk})
    return usuario_cliente, carrinho_com_itens, endereco


def pagar(client, forma, dados=None):
    return client.post(reverse("pedidos:checkout_confirmar"), {"forma_pagamento": forma, **(dados or {})})


@pytest.mark.parametrize("numero,valido", [
    ("4111 1111 1111 1111", True), ("4000000000000002", True),
    ("4111111111111112", False), ("0000000000000000", False), ("abc4111111111111111", False),
])
def test_luhn_confere_numero_do_cartao(numero, valido):
    assert pagamento_service.validar_luhn(numero) is valido


@pytest.mark.parametrize("campo,valor", [
    ("numero", "4111111111111112"), ("validade", "01/20"), ("validade", "13/99"),
    ("validade", "12/2099"), ("cvv", "12"), ("cvv", "1234"), ("cvv", "abc"), ("nome", "  "),
])
def test_validacao_informa_erro_no_campo_correto(dados_cartao, campo, valor):
    dados_cartao[campo] = valor
    with pytest.raises(pagamento_service.ErroPagamento) as erro:
        pagamento_service.validar_cartao(dados_cartao)
    assert campo in erro.value.erros


def test_validade_deve_ser_futura(dados_cartao):
    dados_cartao["validade"] = timezone.localdate().strftime("%m/%y")
    with pytest.raises(pagamento_service.ErroPagamento):
        pagamento_service.validar_cartao(dados_cartao)


@pytest.mark.parametrize("quantidade", [1, 2, 3])
def test_parcelamento_ate_tres_vezes_nao_tem_juros(quantidade):
    resultado = pagamento_service.calcular_parcelas(Decimal("120.00"), quantidade)
    assert resultado["total"] == Decimal("120.00")
    assert resultado["valor_parcela"] == Decimal("120.00") / quantidade


def test_cinco_parcelas_aplicam_juros_compostos_exatos():
    resultado = pagamento_service.calcular_parcelas(Decimal("100.00"), 5)
    assert resultado == {"parcelas": 5, "total": Decimal("113.14"), "valor_parcela": Decimal("22.63")}
    assert len(pagamento_service.opcoes_parcelamento(Decimal("100.00"))) == 12


@pytest.mark.parametrize("quantidade", [0, 13, "abc", "1.5", None])
def test_parcelamento_rejeita_quantidade_invalida(quantidade):
    with pytest.raises(pagamento_service.ErroPagamento):
        pagamento_service.calcular_parcelas(Decimal("100.00"), quantidade)


def test_cartao_recusado_libera_reserva_e_preserva_carrinho_e_estoque(client, compra, dados_cartao):
    usuario, carrinho, _ = compra
    itens = list(carrinho.itens.select_related("produto"))
    dados_cartao["numero"] = "4000 0000 0000 0002"
    resposta = pagar(client, "CARTAO", dados_cartao)
    assert "Pagamento não autorizado. Tente outro cartão ou escolha PIX." in resposta.content.decode()
    assert not Pedido.objects.exists()
    assert not CupomUso.objects.exists()
    assert carrinho.itens.count() == 2
    assert not ReservaEstoque.objects.filter(ativa=True).exists()
    client.get(reverse("pedidos:checkout_pagamento"))
    assert ReservaEstoque.objects.filter(ativa=True, usuario=usuario).exists()
    for item in itens:
        estoque, vendas = item.produto.estoque, item.produto.total_vendas
        item.produto.refresh_from_db()
        assert (item.produto.estoque, item.produto.total_vendas) == (estoque, vendas)


def test_cartao_aprovado_cria_pedido_baixa_estoque_e_limpa_sessao(client, compra, dados_cartao):
    usuario, carrinho, endereco = compra
    itens = list(carrinho.itens.select_related("produto"))
    resposta = pagar(client, "CARTAO", dados_cartao)
    pedido = Pedido.objects.get()
    assert resposta.url == reverse("pedidos:pedido_detalhe", args=[pedido.numero])
    assert pedido.status == "PAGAMENTO_CONFIRMADO"
    assert pedido.estoque_baixado
    assert list(pedido.historico_status.values_list("status", flat=True)) == ["PAGAMENTO_CONFIRMADO"]
    assert not carrinho.itens.exists()
    assert not ReservaEstoque.objects.filter(ativa=True).exists()
    assert not any(chave.startswith(("checkout_", "frete_")) or chave == "cupom_codigo" for chave in client.session.keys())
    assert endereco.logradouro in pedido.endereco_entrega
    for item in itens:
        estoque, vendas = item.produto.estoque, item.produto.total_vendas
        item.produto.refresh_from_db()
        assert (item.produto.estoque, item.produto.total_vendas) == (estoque - item.quantidade, vendas + item.quantidade)
        gravado = pedido.itens.get(produto=item.produto)
        assert (gravado.nome_produto, gravado.preco_unitario, gravado.subtotal) == (item.produto.nome, item.produto.preco, item.subtotal)
    conteudo = client.get(resposta.url).content.decode()
    assert "Acompanhar pedido" in conteudo
    assert "Nenhum valor real será cobrado." in conteudo


def test_numero_completo_e_cvv_nao_ficam_salvos(client, compra, dados_cartao):
    pagar(client, "CARTAO", dados_cartao)
    pedido = Pedido.objects.get()
    salvo = json.dumps(list(Pedido.objects.values()), default=str) + json.dumps(dict(client.session))
    assert dados_cartao["numero"] not in salvo
    assert dados_cartao["numero"].replace(" ", "") not in salvo
    assert "cvv" not in salvo and "validade" not in salvo
    assert pedido.detalhes_pagamento["ultimos_digitos"] == "1111"
    assert pedido.detalhes_pagamento["bandeira"] == "Visa"


def test_pix_reserva_por_trinta_minutos_sem_baixar_estoque(client, compra):
    usuario, carrinho, _ = compra
    instante = timezone.now()
    with patch("django.utils.timezone.now", return_value=instante):
        resposta = pagar(client, "PIX")
    pedido = Pedido.objects.get()
    assert pedido.status == "AGUARDANDO_PAGAMENTO"
    assert not pedido.estoque_baixado
    assert pedido.pix_expira_em == instante + timedelta(minutes=30)
    assert ReservaEstoque.objects.filter(ativa=True, expira_em=pedido.pix_expira_em).count() == 2
    assert not carrinho.itens.exists()
    assert list(pedido.historico_status.values_list("status", flat=True)) == ["AGUARDANDO_PAGAMENTO"]
    conteudo = client.get(resposta.url).content.decode()
    assert "Confirmar pagamento (simulação)" in conteudo
    assert "data-expira-em" in conteudo
    assert "Nenhum valor real será cobrado." in conteudo


def test_qr_ficticio_e_svg_deterministico():
    primeiro = pagamento_service.desenhar_qr("DEMONSTRACAO-001")
    assert primeiro == pagamento_service.desenhar_qr("DEMONSTRACAO-001")
    assert primeiro != pagamento_service.desenhar_qr("DEMONSTRACAO-002")
    assert ElementTree.fromstring(primeiro).tag == "{http://www.w3.org/2000/svg}svg"
    assert "<script" not in pagamento_service.desenhar_qr("<script>alert(1)</script>")


def test_confirmar_pix_duas_vezes_baixa_uma_vez_e_registra_cupom_uma_vez(client, compra, cupom_valido):
    sessao = client.session
    sessao["cupom_codigo"] = cupom_valido.codigo
    sessao.save()
    pagar(client, "PIX")
    pedido = Pedido.objects.get()
    item = pedido.itens.select_related("produto").first()
    estoque, vendas = item.produto.estoque, item.produto.total_vendas
    for _ in range(2):
        resposta = client.post(reverse("pedidos:confirmar_pix", args=[pedido.numero]))
        assert resposta.status_code == 302
    pedido.refresh_from_db()
    item.produto.refresh_from_db()
    assert pedido.status == "PAGAMENTO_CONFIRMADO"
    assert (item.produto.estoque, item.produto.total_vendas) == (estoque - item.quantidade, vendas + item.quantidade)
    assert list(pedido.historico_status.values_list("status", flat=True)) == ["AGUARDANDO_PAGAMENTO", "PAGAMENTO_CONFIRMADO"]
    assert CupomUso.objects.filter(cupom=cupom_valido, usuario=compra[0]).count() == 1


@pytest.mark.parametrize("confirmar", [False, True])
def test_pix_expirado_cancela_libera_reserva_e_desfaz_cupom(client, compra, cupom_valido, confirmar):
    sessao = client.session
    sessao["cupom_codigo"] = cupom_valido.codigo
    sessao.save()
    pagar(client, "PIX")
    pedido = Pedido.objects.get()
    itens = list(pedido.itens.select_related("produto"))
    with patch("django.utils.timezone.now", return_value=pedido.pix_expira_em):
        if confirmar:
            resposta = client.post(reverse("pedidos:confirmar_pix", args=[pedido.numero]), follow=True)
        else:
            resposta = client.get(reverse("pedidos:pedido_detalhe", args=[pedido.numero]))
    assert "PIX expirado" in resposta.content.decode()
    pedido.refresh_from_db()
    assert pedido.status == "CANCELADO"
    assert not pedido.estoque_baixado
    assert not ReservaEstoque.objects.filter(ativa=True).exists()
    assert not CupomUso.objects.exists()
    assert list(pedido.historico_status.values_list("status", flat=True)) == ["AGUARDANDO_PAGAMENTO", "CANCELADO"]
    pedido_service.confirmar_pix(pedido, compra[0])
    assert pedido.historico_status.count() == 2
    for item in itens:
        estoque, vendas = item.produto.estoque, item.produto.total_vendas
        item.produto.refresh_from_db()
        assert (item.produto.estoque, item.produto.total_vendas) == (estoque, vendas)


def test_item_esgotado_antes_de_confirmar_volta_ao_carrinho_sem_pedido(client, compra, dados_cartao):
    produto = compra[1].itens.first().produto
    produto.estoque = 0
    produto.save()
    ReservaEstoque.objects.update(expira_em=timezone.now() - timedelta(seconds=1))
    resposta = pagar(client, "CARTAO", dados_cartao)
    assert resposta.url == reverse("carrinho:detalhe")
    assert not Pedido.objects.exists()


def test_outro_usuario_nao_acessa_nem_confirma_pedido(client, compra, usuario_admin):
    pagar(client, "PIX")
    pedido = Pedido.objects.get()
    client.force_login(usuario_admin)
    assert client.get(reverse("pedidos:pedido_detalhe", args=[pedido.numero])).status_code == 404
    assert client.post(reverse("pedidos:confirmar_pix", args=[pedido.numero])).status_code == 404
    pedido.refresh_from_db()
    assert not pedido.estoque_baixado
    assert pedido.historico_status.count() == 1


def test_cartao_pago_registra_cupom_uma_vez_mesmo_reenviando_formulario(client, compra, dados_cartao, cupom_valido):
    sessao = client.session
    sessao["cupom_codigo"] = cupom_valido.codigo
    sessao.save()
    pagar(client, "CARTAO", dados_cartao)
    pagar(client, "CARTAO", dados_cartao)
    assert Pedido.objects.count() == 1
    assert CupomUso.objects.count() == 1
    assert Pedido.objects.get().valor_desconto == Decimal("3.60")


def test_novo_carrinho_preserva_reservas_do_pix_pendente(client, compra):
    pagar(client, "PIX")
    pedido = Pedido.objects.get()
    produto = pedido.itens.first().produto
    carrinho_service.adicionar(compra[1], produto, 1)
    assert ReservaEstoque.objects.filter(ativa=True, expira_em=pedido.pix_expira_em).count() == 2
    resposta = client.get(reverse("pedidos:checkout_endereco"))
    assert resposta.url == reverse("pedidos:pedido_detalhe", args=[pedido.numero])
    assert Pedido.objects.count() == 1


def test_falha_na_baixa_desfaz_pedido_itens_historico_e_cupom(client, compra, dados_cartao, cupom_valido):
    usuario, carrinho, endereco = compra
    sessao = {"cupom_codigo": cupom_valido.codigo}
    with patch.object(estoque_service, "dar_baixa", side_effect=estoque_service.ErroEstoque):
        with pytest.raises(estoque_service.ErroEstoque):
            pedido_service.criar_pedido(usuario, carrinho, endereco, sessao, "CARTAO", dados_cartao)
    assert not Pedido.objects.exists()
    assert not CupomUso.objects.exists()
    assert not HistoricoStatus.objects.exists()
    assert carrinho.itens.count() == 2
    assert sessao["cupom_codigo"] == cupom_valido.codigo
