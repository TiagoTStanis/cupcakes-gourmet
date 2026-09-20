from datetime import timedelta
import pytest
from django.urls import reverse
from django.utils import timezone

from carrinho.models import Carrinho
from pedidos.models import ItemPedido, Pedido


pytestmark = pytest.mark.django_db


def _criar_pedido(usuario, numero="CG-HIST-01", total="25.00", itens=None, criado_em=None):
    pedido = Pedido.objects.create(
        numero=numero,
        usuario=usuario,
        endereco_entrega="Rua Paraná, 120\nCentro — Cascavel/PR\nCEP 85801-000",
        subtotal=total,
        valor_frete="0.00",
        valor_total=total,
        forma_pagamento="CARTAO",
        status="PAGAMENTO_CONFIRMADO",
    )
    if criado_em:
        Pedido.objects.filter(pk=pedido.pk).update(criado_em=criado_em)
        pedido.refresh_from_db()

    if itens:
        for produto, qtd in itens:
            ItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                nome_produto=produto.nome,
                preco_unitario=produto.preco,
                quantidade=qtd,
                subtotal=produto.preco * qtd,
            )
    return pedido


def test_historico_exige_login(client):
    resposta = client.get(reverse("pedidos:historico"))
    assert resposta.status_code == 302
    assert reverse("usuarios:login") in resposta["Location"]


def test_historico_lista_apenas_pedidos_do_proprio_usuario(client, usuario_cliente, usuario_admin, produtos_com_estoque):
    p_cliente = _criar_pedido(usuario_cliente, numero="CG-CLIENTE-1", itens=[(produtos_com_estoque[0], 2)])
    p_admin = _criar_pedido(usuario_admin, numero="CG-ADMIN-1", itens=[(produtos_com_estoque[1], 1)])

    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:historico"))
    assert resposta.status_code == 200

    pedidos_listados = list(resposta.context["pedidos"])
    assert p_cliente in pedidos_listados
    assert p_admin not in pedidos_listados

    conteudo = resposta.content.decode()
    assert p_cliente.numero in conteudo
    assert p_admin.numero not in conteudo


def test_historico_ordem_do_mais_recente_ao_mais_antigo(client, usuario_cliente):
    agora = timezone.now()
    p1 = _criar_pedido(usuario_cliente, numero="CG-ANTIGO", criado_em=agora - timedelta(days=10))
    p2 = _criar_pedido(usuario_cliente, numero="CG-MEIO", criado_em=agora - timedelta(days=2))
    p3 = _criar_pedido(usuario_cliente, numero="CG-NOVO", criado_em=agora)

    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:historico"))
    assert list(resposta.context["pedidos"]) == [p3, p2, p1]


def test_historico_paginacao_com_dez_por_pagina(client, usuario_cliente):
    agora = timezone.now()
    for i in range(1, 24):
        _criar_pedido(usuario_cliente, numero=f"CG-PAG-{i:02d}", criado_em=agora + timedelta(minutes=i))

    client.force_login(usuario_cliente)

    resp_p1 = client.get(reverse("pedidos:historico"))
    assert len(resp_p1.context["pedidos"]) == 10
    assert resp_p1.context["pagina"].paginator.count == 23
    assert resp_p1.context["pagina"].paginator.num_pages == 3
    assert "Página 1 de 3" in resp_p1.content.decode()

    resp_p2 = client.get(reverse("pedidos:historico") + "?pagina=2")
    assert len(resp_p2.context["pedidos"]) == 10
    assert "Página 2 de 3" in resp_p2.content.decode()

    resp_p3 = client.get(reverse("pedidos:historico") + "?pagina=3")
    assert len(resp_p3.context["pedidos"]) == 3
    assert "Página 3 de 3" in resp_p3.content.decode()


def test_historico_estado_vazio(client, usuario_cliente):
    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:historico"))
    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert "Você ainda não fez nenhum pedido. Que tal começar agora?" in conteudo
    assert reverse("catalogo:vitrine") in conteudo


def test_repetir_pedido_adiciona_itens_ao_carrinho(client, usuario_cliente, produtos_com_estoque):
    p1, p2 = produtos_com_estoque[0], produtos_com_estoque[1]
    pedido = _criar_pedido(usuario_cliente, numero="CG-REPETE-OK", itens=[(p1, 2), (p2, 3)])

    client.force_login(usuario_cliente)
    resposta = client.post(reverse("pedidos:repetir_pedido", args=[pedido.numero]))
    assert resposta.status_code == 302
    assert resposta["Location"] == reverse("carrinho:detalhe")

    carrinho = Carrinho.objects.get(usuario=usuario_cliente)
    assert carrinho.itens.get(produto=p1).quantidade == 2
    assert carrinho.itens.get(produto=p2).quantidade == 3


def test_repetir_pedido_respeita_limite_de_dez_unidades(client, usuario_cliente, produtos_com_estoque):
    from carrinho.services import carrinho_service

    prod = produtos_com_estoque[0]
    carrinho = carrinho_service.obter_carrinho(usuario_cliente)
    carrinho_service.adicionar(carrinho, prod, quantidade=8)

    pedido = _criar_pedido(usuario_cliente, numero="CG-LIMITE", itens=[(prod, 4)])

    client.force_login(usuario_cliente)
    resposta = client.post(reverse("pedidos:repetir_pedido", args=[pedido.numero]), follow=True)
    assert resposta.status_code == 200

    carrinho.refresh_from_db()
    assert carrinho.itens.get(produto=prod).quantidade == 8
    assert "10 unidades" in resposta.content.decode()


def test_repetir_pedido_respeita_estoque_disponivel_e_informa_falta(client, usuario_cliente, produtos_com_estoque):
    prod = produtos_com_estoque[1]
    prod.estoque = 1
    prod.save()

    pedido = _criar_pedido(usuario_cliente, numero="CG-ESTOQUE-BAIXO", itens=[(prod, 4)])

    client.force_login(usuario_cliente)
    resposta = client.post(reverse("pedidos:repetir_pedido", args=[pedido.numero]), follow=True)
    assert resposta.status_code == 200

    conteudo = resposta.content.decode()
    assert prod.nome in conteudo
    assert "disponíveis" in conteudo or "estoque" in conteudo


def test_repetir_pedido_ignora_produto_inativo_com_mensagem(client, usuario_cliente, produtos_com_estoque):
    p_ativo = produtos_com_estoque[0]
    p_inativo = produtos_com_estoque[2]
    p_inativo.ativo = False
    p_inativo.save()

    pedido = _criar_pedido(usuario_cliente, numero="CG-INATIVO", itens=[(p_ativo, 2), (p_inativo, 1)])

    client.force_login(usuario_cliente)
    resposta = client.post(reverse("pedidos:repetir_pedido", args=[pedido.numero]), follow=True)
    assert resposta.status_code == 200

    carrinho = Carrinho.objects.get(usuario=usuario_cliente)
    assert carrinho.itens.filter(produto=p_ativo).exists()
    assert not carrinho.itens.filter(produto=p_inativo).exists()
    assert f"{p_inativo.nome} não está mais disponível." in resposta.content.decode()


def test_repetir_pedido_nao_cria_pedido_nem_altera_estoque(client, usuario_cliente, produtos_com_estoque):
    prod = produtos_com_estoque[0]
    estoque_inicial = prod.estoque
    pedido = _criar_pedido(usuario_cliente, numero="CG-SEM-ALTERACAO", itens=[(prod, 2)])
    total_pedidos = Pedido.objects.count()

    client.force_login(usuario_cliente)
    client.post(reverse("pedidos:repetir_pedido", args=[pedido.numero]))

    assert Pedido.objects.count() == total_pedidos
    prod.refresh_from_db()
    assert prod.estoque == estoque_inicial


def test_outro_usuario_nao_consegue_repetir_pedido_alheio(client, usuario_cliente, usuario_admin, produtos_com_estoque):
    pedido = _criar_pedido(usuario_cliente, numero="CG-OUTRO-DONO", itens=[(produtos_com_estoque[0], 1)])

    client.force_login(usuario_admin)
    resposta = client.post(reverse("pedidos:repetir_pedido", args=[pedido.numero]))
    assert resposta.status_code in (403, 404)

    carrinho_admin = Carrinho.objects.filter(usuario=usuario_admin).first()
    assert carrinho_admin is None or carrinho_admin.itens.count() == 0


def test_repetir_pedido_exige_metodo_post(client, usuario_cliente, produtos_com_estoque):
    pedido = _criar_pedido(usuario_cliente, numero="CG-GET-INVALIDO", itens=[(produtos_com_estoque[0], 1)])

    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:repetir_pedido", args=[pedido.numero]))
    assert resposta.status_code == 405


def test_aba_pedidos_destacada_no_historico_rastreamento_e_notificacoes(client, usuario_cliente, produtos_com_estoque):
    pedido = _criar_pedido(usuario_cliente, numero="CG-NAV-ABA", itens=[(produtos_com_estoque[0], 1)])

    client.force_login(usuario_cliente)

    resp_historico = client.get(reverse("pedidos:historico"))
    assert 'class="ativo" aria-current="page"' in resp_historico.content.decode()

    resp_rastreio = client.get(reverse("pedidos:pedido_detalhe", args=[pedido.numero]))
    assert 'class="ativo" aria-current="page"' in resp_rastreio.content.decode()

    resp_notif = client.get(reverse("pedidos:notificacoes"))
    assert 'class="ativo" aria-current="page"' in resp_notif.content.decode()

    resp_inicio = client.get(reverse("inicio"))
    assert 'href="/pedidos/" class="ativo"' not in resp_inicio.content.decode()


def test_cartao_mostra_dados_status_e_acoes(client, usuario_cliente, produtos_com_estoque):
    prod = produtos_com_estoque[0]
    pedido = _criar_pedido(usuario_cliente, numero="CG-DETALHES-CARD", total="25.00", itens=[(prod, 2)])

    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:historico"))
    conteudo = resposta.content.decode()

    assert pedido.numero in conteudo
    assert "25,00" in conteudo
    assert "2 itens" in conteudo
    assert pedido.get_status_display() in conteudo
    assert reverse("pedidos:pedido_detalhe", args=[pedido.numero]) in conteudo
    assert reverse("pedidos:repetir_pedido", args=[pedido.numero]) in conteudo
    assert "Ver detalhes" in conteudo
    assert "Repetir pedido" in conteudo
