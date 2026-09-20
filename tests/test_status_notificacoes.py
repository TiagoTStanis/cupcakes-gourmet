from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from pedidos.models import CupomUso, HistoricoStatus, ItemPedido, Notificacao, Pedido, ReservaEstoque, TabelaFreteUF
from pedidos.services import pedido_service
from usuarios.models import Endereco


pytestmark = pytest.mark.django_db


@pytest.fixture
def pedido(usuario_cliente, produtos_com_estoque):
    atual = Pedido.objects.create(
        numero="CG-TESTE", usuario=usuario_cliente,
        endereco_entrega="Rua Paraná, 120\nCentro — Cascavel/PR\nCEP 85801-000",
        subtotal="25.00", valor_frete="10.00", valor_total="35.00", forma_pagamento="PIX",
        pix_expira_em=timezone.now() + timedelta(minutes=30), detalhes_pagamento={"codigo": "TESTE"},
    )
    produto = produtos_com_estoque[0]
    ItemPedido.objects.create(pedido=atual, produto=produto, nome_produto=produto.nome,
                              preco_unitario=produto.preco, quantidade=2, subtotal="25.00")
    ReservaEstoque.objects.create(usuario=usuario_cliente, produto=produto, quantidade=2, expira_em=atual.pix_expira_em)
    return atual


def test_transicoes_validas_gravam_historico_e_notificacoes(pedido):
    for status in ["PAGAMENTO_CONFIRMADO", "EM_PREPARACAO", "SAIU_PARA_ENTREGA", "ENTREGUE"]:
        pedido_service.alterar_status(pedido, status)
        assert pedido.historico_status.filter(status=status).count() == 1
        aviso = Notificacao.objects.first()
        assert aviso.usuario == pedido.usuario and aviso.pedido == pedido
        assert aviso.titulo == pedido.get_status_display()
    assert pedido.historico_status.count() == Notificacao.objects.count() == 4


@pytest.mark.parametrize("origem,destino", [
    ("AGUARDANDO_PAGAMENTO", "EM_PREPARACAO"), ("PAGAMENTO_CONFIRMADO", "AGUARDANDO_PAGAMENTO"),
    ("PAGAMENTO_CONFIRMADO", "CANCELADO"), ("SAIU_PARA_ENTREGA", "CANCELADO"),
    ("ENTREGUE", "CANCELADO"), ("ENTREGUE", "EM_PREPARACAO"), ("CANCELADO", "PAGAMENTO_CONFIRMADO"),
    ("AGUARDANDO_PAGAMENTO", "INEXISTENTE"),
])
def test_transicao_invalida_preserva_status_estoque_e_avisos(pedido, origem, destino):
    Pedido.objects.filter(pk=pedido.pk).update(status=origem)
    produto = pedido.itens.first().produto
    estoque = produto.estoque
    with pytest.raises(pedido_service.ErroPedido, match="Não é permitido"):
        pedido_service.alterar_status(pedido, destino)
    pedido.refresh_from_db()
    produto.refresh_from_db()
    assert pedido.status == origem and produto.estoque == estoque
    assert not HistoricoStatus.objects.exists() and not Notificacao.objects.exists()


@pytest.mark.parametrize("preparacao", [False, True])
def test_cancelamento_repoe_so_a_baixa_e_repeticao_nao_duplica(pedido, preparacao):
    produto = pedido.itens.first().produto
    estoque, vendas = produto.estoque, produto.total_vendas
    if preparacao:
        pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
        pedido_service.alterar_status(pedido, "EM_PREPARACAO")
    pedido_service.alterar_status(pedido, "CANCELADO", motivo="Solicitado pelo cliente")
    with pytest.raises(pedido_service.ErroPedido):
        pedido_service.alterar_status(pedido, "CANCELADO")
    produto.refresh_from_db()
    assert (produto.estoque, produto.total_vendas) == (estoque, vendas)
    assert not pedido.estoque_baixado
    assert not ReservaEstoque.objects.filter(ativa=True).exists()
    assert pedido.historico_status.filter(status="CANCELADO").count() == 1
    assert "Solicitado pelo cliente" in Notificacao.objects.first().mensagem


@pytest.mark.parametrize("pago", [False, True])
def test_cupom_so_e_devolvido_no_cancelamento_nao_pago(pedido, cupom_valido, pago):
    pedido.cupom = cupom_valido
    pedido.save()
    CupomUso.objects.create(cupom=cupom_valido, usuario=pedido.usuario)
    if pago:
        pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
        pedido_service.alterar_status(pedido, "EM_PREPARACAO")
    pedido_service.alterar_status(pedido, "CANCELADO")
    assert CupomUso.objects.exists() is pago


def test_cancelamento_preserva_reservas_de_novo_carrinho(pedido):
    pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
    pedido_service.alterar_status(pedido, "EM_PREPARACAO")
    ReservaEstoque.objects.update(ativa=True, expira_em=timezone.now() + timedelta(minutes=10))
    pedido_service.alterar_status(pedido, "CANCELADO")
    assert ReservaEstoque.objects.filter(ativa=True).exists()


def test_pix_confirmado_notifica_uma_vez(pedido):
    for _ in range(2):
        pedido_service.confirmar_pix(pedido, pedido.usuario)
    assert Notificacao.objects.get().titulo == "Pagamento confirmado"


def test_pix_expirado_notifica_cancelamento_uma_vez(pedido, client):
    client.force_login(pedido.usuario)
    with patch("django.utils.timezone.now", return_value=pedido.pix_expira_em):
        for _ in range(2):
            resposta = client.get(reverse("pedidos:pedido_detalhe", args=[pedido.numero]))
    assert "PIX expirado" in resposta.content.decode()
    assert "Pedido cancelado" in resposta.content.decode()
    assert Notificacao.objects.count() == 1
    assert not ReservaEstoque.objects.filter(ativa=True).exists()


def test_cartao_confirmado_cria_notificacao(usuario_cliente, carrinho_com_itens, tabela_frete):
    endereco = Endereco.objects.create(usuario=usuario_cliente, cep="85801-000", logradouro="Rua Paraná",
                                       numero="120", bairro="Centro", cidade="Cascavel", uf="PR")
    atual = pedido_service.criar_pedido(usuario_cliente, carrinho_com_itens, endereco, {}, "CARTAO", {
        "numero": "4111111111111111", "validade": "12/99", "cvv": "123", "nome": "Marina Souza", "parcelas": "1",
    })
    assert Notificacao.objects.get(pedido=atual).titulo == "Pagamento confirmado"


def test_falha_no_aviso_desfaz_transicao_e_baixa(pedido):
    produto = pedido.itens.first().produto
    estoque = produto.estoque
    with patch.object(Notificacao.objects, "create", side_effect=RuntimeError("Falha no banco")):
        with pytest.raises(RuntimeError):
            pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
    pedido.refresh_from_db()
    produto.refresh_from_db()
    assert pedido.status == "AGUARDANDO_PAGAMENTO" and produto.estoque == estoque
    assert not HistoricoStatus.objects.exists()


def test_sino_conta_apenas_nao_lidas_do_dono_e_zero_para_visitante(client, pedido, usuario_admin):
    pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
    Notificacao.objects.create(usuario=usuario_admin, titulo="Privada", mensagem="Outro usuário")
    Notificacao.objects.create(usuario=pedido.usuario, titulo="Antiga", mensagem="Já vista", lida=True)
    assert client.get(reverse("inicio")).context["notificacoes_nao_lidas"] == 0
    client.force_login(pedido.usuario)
    resposta = client.get(reverse("inicio"))
    assert resposta.context["notificacoes_nao_lidas"] == 1
    assert 'id="badge-notificacoes">1</span>' in resposta.content.decode()


def test_marcar_uma_ou_todas_exige_post_e_preserva_outro_dono(client, pedido, usuario_admin):
    pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
    aviso = Notificacao.objects.get()
    alheio = Notificacao.objects.create(usuario=usuario_admin, titulo="Privada", mensagem="Outro usuário")
    client.force_login(pedido.usuario)
    uma = reverse("pedidos:marcar_notificacao_lida", args=[aviso.pk])
    todas = reverse("pedidos:marcar_todas_lidas")
    assert client.get(uma).status_code == client.get(todas).status_code == 405
    assert client.post(reverse("pedidos:marcar_notificacao_lida", args=[alheio.pk])).status_code == 404
    assert client.post(uma).status_code == 302
    aviso.refresh_from_db()
    assert aviso.lida
    Notificacao.objects.create(usuario=pedido.usuario, titulo="Nova", mensagem="Novo aviso")
    assert client.post(todas).status_code == 302
    assert not Notificacao.objects.filter(usuario=pedido.usuario, lida=False).exists()
    alheio.refresh_from_db()
    assert not alheio.lida


def test_rastreamento_mostra_etapas_horarios_e_prazo_da_uf(client, pedido, tabela_frete):
    pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
    pedido_service.alterar_status(pedido, "EM_PREPARACAO")
    client.force_login(pedido.usuario)
    resposta = client.get(reverse("pedidos:pedido_detalhe", args=[pedido.numero]))
    conteudo = resposta.content.decode()
    for nome in ["Pagamento confirmado", "Em preparação", "Saiu para entrega", "Entregue"]:
        assert nome in conteudo
    for registro in pedido.historico_status.all():
        assert timezone.localtime(registro.criado_em).strftime("%d/%m/%Y %H:%M") in conteudo
    assert conteudo.count('aria-current="step"') == 1
    esperado = timezone.localdate() + timedelta(days=TabelaFreteUF.objects.get(uf="PR").prazo_dias)
    assert resposta.context["previsao_entrega"] == esperado
    assert "Nenhum valor real será cobrado." in conteudo
    TabelaFreteUF.objects.all().delete()
    assert "Previsão de entrega" not in client.get(resposta.wsgi_request.path).content.decode()


def test_pix_pendente_tambem_mostra_etapas(client, pedido):
    client.force_login(pedido.usuario)
    conteudo = client.get(reverse("pedidos:pedido_detalhe", args=[pedido.numero])).content.decode()
    assert "Pagamento confirmado" in conteudo and "Entregue" in conteudo
    assert 'aria-current="step"' not in conteudo


def test_outro_usuario_nao_ve_pedido_nem_notificacoes(client, pedido, usuario_admin):
    pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
    client.force_login(usuario_admin)
    assert client.get(reverse("pedidos:pedido_detalhe", args=[pedido.numero])).status_code == 404
    resposta = client.get(reverse("pedidos:notificacoes"))
    assert list(resposta.context["notificacoes"]) == []
    assert pedido.numero not in resposta.content.decode()
    client.logout()
    assert client.get(reverse("pedidos:notificacoes")).status_code == 302


def test_lista_notificacoes_mais_recentes_primeiro_com_link_e_aviso(client, pedido):
    pedido_service.alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
    pedido_service.alterar_status(pedido, "EM_PREPARACAO")
    client.force_login(pedido.usuario)
    resposta = client.get(reverse("pedidos:notificacoes"))
    assert [aviso.titulo for aviso in resposta.context["notificacoes"]] == ["Em preparação", "Pagamento confirmado"]
    conteudo = resposta.content.decode()
    assert reverse("pedidos:pedido_detalhe", args=[pedido.numero]) in conteudo
    assert "Não chegam por push no celular." in conteudo
