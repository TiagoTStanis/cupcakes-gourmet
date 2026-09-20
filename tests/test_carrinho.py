from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from carrinho.models import Carrinho, ItemCarrinho
from carrinho.services import carrinho_service as servico
from carrinho.services.carrinho_service import ErroCarrinho
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def test_bloqueio_da_11a_unidade_ao_adicionar_ao_carrinho(usuario_cliente, produtos_com_estoque):
    produto = produtos_com_estoque[0]
    carrinho = servico.obter_carrinho(usuario_cliente)

    servico.adicionar(carrinho, produto, quantidade=10)
    assert carrinho.itens.get(produto=produto).quantidade == 10

    with pytest.raises(ErroCarrinho) as erro:
        servico.adicionar(carrinho, produto, quantidade=1)
    assert "no máximo 10 unidades de cada cupcake" in str(erro.value) or "no maximo 10 unidades de cada cupcake" in str(erro.value)

    with pytest.raises(ErroCarrinho) as erro_direto:
        servico.alterar_quantidade(carrinho, produto, quantidade=11)
    assert "no máximo 10 unidades de cada cupcake" in str(erro_direto.value) or "no maximo 10 unidades de cada cupcake" in str(erro_direto.value)


def test_bloqueio_de_quantidade_acima_do_estoque_disponivel(usuario_cliente, produtos_com_estoque):
    produto = produtos_com_estoque[1]
    carrinho = servico.obter_carrinho(usuario_cliente)

    with pytest.raises(ErroCarrinho) as erro:
        servico.adicionar(carrinho, produto, quantidade=produto.estoque + 1)
    assert f"Só temos {produto.estoque} unidades disponíveis" in str(erro.value) or f"So temos {produto.estoque} unidades disponiveis" in str(erro.value)

    with pytest.raises(ErroCarrinho):
        servico.alterar_quantidade(carrinho, produto, quantidade=produto.estoque + 2)


def test_remocao_de_item_ao_alterar_quantidade_para_zero(usuario_cliente, produtos_com_estoque):
    produto = produtos_com_estoque[0]
    carrinho = servico.obter_carrinho(usuario_cliente)

    servico.adicionar(carrinho, produto, quantidade=3)
    assert carrinho.itens.filter(produto=produto).exists()

    resultado = servico.alterar_quantidade(carrinho, produto, quantidade=0)
    assert resultado is None
    assert not carrinho.itens.filter(produto=produto).exists()

    servico.adicionar(carrinho, produto, quantidade=2)
    servico.remover(carrinho, produto)
    assert not carrinho.itens.filter(produto=produto).exists()


def test_carrinho_expira_e_zera_itens_apos_24_horas(usuario_cliente, produtos_com_estoque):
    produto = produtos_com_estoque[0]
    carrinho = servico.obter_carrinho(usuario_cliente)
    servico.adicionar(carrinho, produto, quantidade=2)
    assert carrinho.itens.count() == 1

    vinte_e_cinco_horas_atras = timezone.now() - timedelta(hours=25)
    Carrinho.objects.filter(id=carrinho.id).update(atualizado_em=vinte_e_cinco_horas_atras)

    carrinho_renovado = servico.obter_carrinho(usuario_cliente)
    assert carrinho_renovado.itens.count() == 0


def test_visitante_e_redirecionado_ao_login_com_mensagem_contextual(client, produtos_com_estoque):
    produto = produtos_com_estoque[0]

    resposta_get = client.get(reverse("carrinho:detalhe"))
    assert resposta_get.status_code == 302
    assert reverse("usuarios:login") in resposta_get.url
    assert "next=" in resposta_get.url

    mensagens_get = [m.message for m in get_messages(resposta_get.wsgi_request)]
    assert any("Entre na sua conta para adicionar itens ao carrinho" in m for m in mensagens_get)

    resposta_post = client.post(reverse("carrinho:adicionar"), {"produto_id": produto.id, "quantidade": 1})
    assert resposta_post.status_code == 302
    assert reverse("usuarios:login") in resposta_post.url


def test_calculo_do_total_geral_e_subtotal_com_decimal(usuario_cliente, produtos_com_estoque):
    produto_a = produtos_com_estoque[0]
    produto_b = produtos_com_estoque[1]
    carrinho = servico.obter_carrinho(usuario_cliente)

    item_a = servico.adicionar(carrinho, produto_a, quantidade=2)
    item_b = servico.adicionar(carrinho, produto_b, quantidade=3)

    subtotal_esperado_a = Decimal("12.50") * 2
    subtotal_esperado_b = Decimal("11.00") * 3
    total_esperado = subtotal_esperado_a + subtotal_esperado_b

    assert isinstance(item_a.subtotal, Decimal)
    assert item_a.subtotal == Decimal("25.00")
    assert item_b.subtotal == Decimal("33.00")
    assert isinstance(carrinho.total_geral, Decimal)
    assert carrinho.total_geral == total_esperado


def test_produto_inativo_recusado_ao_adicionar_ao_carrinho(usuario_cliente, produtos_com_estoque):
    produto = produtos_com_estoque[0]
    produto.ativo = False
    produto.save()

    carrinho = servico.obter_carrinho(usuario_cliente)

    with pytest.raises(ErroCarrinho) as erro:
        servico.adicionar(carrinho, produto, quantidade=1)
    assert "não está mais disponível" in str(erro.value) or "nao esta mais disponivel" in str(erro.value)


def test_endpoint_json_adicionar_alterar_e_remover_devolve_totais(usuario_cliente, produtos_com_estoque, client):
    client.force_login(usuario_cliente)
    produto = produtos_com_estoque[0]

    resposta_add = client.post(
        reverse("carrinho:adicionar"),
        {"produto_id": produto.id, "quantidade": 2},
    )
    assert resposta_add.status_code == 200
    dados_add = resposta_add.json()
    assert dados_add["sucesso"] is True
    assert dados_add["quantidade"] == 2
    assert dados_add["subtotal_item"] == "25.00"
    assert dados_add["total_geral"] == "25.00"
    assert dados_add["quantidade_total"] == 2

    resposta_alt = client.post(
        reverse("carrinho:alterar"),
        {"produto_id": produto.id, "quantidade": 1},
    )
    assert resposta_alt.status_code == 200
    dados_alt = resposta_alt.json()
    assert dados_alt["sucesso"] is True
    assert dados_alt["quantidade"] == 1
    assert dados_alt["subtotal_item"] == "12.50"
    assert dados_alt["total_geral"] == "12.50"
    assert dados_alt["quantidade_total"] == 1

    resposta_rem = client.post(
        reverse("carrinho:remover"),
        {"produto_id": produto.id},
    )
    assert resposta_rem.status_code == 200
    dados_rem = resposta_rem.json()
    assert dados_rem["sucesso"] is True
    assert dados_rem["quantidade"] == 0
    assert dados_rem["total_geral"] == "0.00"
    assert dados_rem["quantidade_total"] == 0

    resposta_erro = client.post(
        reverse("carrinho:adicionar"),
        {"produto_id": produto.id, "quantidade": 50},
    )
    assert resposta_erro.status_code == 400
    dados_erro = resposta_erro.json()
    assert dados_erro["sucesso"] is False
    assert "erro" in dados_erro


def test_usuario_nao_ve_carrinho_de_outro_usuario(usuario_cliente, produtos_com_estoque, client):
    outro_usuario = Usuario.objects.create_user(
        "outro@teste.com",
        "Outro@123456",
        nome_completo="Outro Cliente",
        email_confirmado=True,
    )

    carrinho_cliente = servico.obter_carrinho(usuario_cliente)
    servico.adicionar(carrinho_cliente, produtos_com_estoque[0], quantidade=2)

    carrinho_outro = servico.obter_carrinho(outro_usuario)
    assert carrinho_outro.itens.count() == 0

    client.force_login(outro_usuario)
    resposta = client.get(reverse("carrinho:detalhe"))
    assert resposta.status_code == 200
    assert produtos_com_estoque[0].nome not in resposta.content.decode()
    assert "Seu carrinho está vazio" in resposta.content.decode()


def test_context_processor_fornece_zero_para_visitante_e_total_para_usuario(usuario_cliente, produtos_com_estoque, client):
    resposta_visitante = client.get(reverse("catalogo:vitrine"))
    assert resposta_visitante.context["carrinho_total_itens"] == 0

    carrinho = servico.obter_carrinho(usuario_cliente)
    servico.adicionar(carrinho, produtos_com_estoque[0], quantidade=3)

    client.force_login(usuario_cliente)
    resposta_logado = client.get(reverse("catalogo:vitrine"))
    assert resposta_logado.context["carrinho_total_itens"] == 3
