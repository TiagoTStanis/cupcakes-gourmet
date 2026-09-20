from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.views.defaults import server_error

from catalogo.models import Categoria, Produto
from pedidos.models import Cupom, Pedido, TabelaFreteUF
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def test_pagina_404_renderiza_template_com_status_404(client, settings):
    settings.DEBUG = False
    settings.ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
    resposta = client.get("/pagina-inexistente-na-loja/")
    assert resposta.status_code == 404
    conteudo = resposta.content.decode("utf-8")
    assert "Página Não Encontrada" in conteudo
    assert "Voltar para o início" in conteudo


def test_pagina_500_renderiza_template_sem_depender_do_banco(rf):
    requisicao = rf.get("/")
    resposta = server_error(requisicao)
    assert resposta.status_code == 500
    conteudo = resposta.content.decode("utf-8")
    assert "Erro no Servidor" in conteudo
    assert "Voltar para o início" in conteudo


def test_pagina_offline_responde_status_200(client):
    resposta = client.get("/offline/")
    assert resposta.status_code == 200
    conteudo = resposta.content.decode("utf-8")
    assert "Sem conexão com a internet. Verifique sua rede e tente de novo" in conteudo
    assert "Recarregar página" in conteudo


def test_popular_dados_cria_doze_produtos_com_imagem_no_disco(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("popular_dados")

    produtos = list(Produto.objects.all())
    assert len(produtos) == 12

    for p in produtos:
        assert p.imagem
        caminho_imagem = Path(settings.MEDIA_ROOT) / p.imagem.name
        assert caminho_imagem.exists()
        assert caminho_imagem.stat().st_size > 0

    assert Categoria.objects.count() == 3
    assert set(Categoria.objects.values_list("slug", flat=True)) == {"classicos", "veganos", "tematicos"}

    assert TabelaFreteUF.objects.filter(uf="PR").exists()
    assert TabelaFreteUF.objects.count() >= 6

    cupom = Cupom.objects.get(codigo="CUPCAKE10")
    assert cupom.tipo == "PERCENTUAL"
    assert cupom.valor == Decimal("10.00")
    assert cupom.valor_minimo_pedido == Decimal("30.00")
    assert cupom.ativo is True

    admin = Usuario.objects.get(email="admin@cupcakesgourmet.com")
    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert admin.email_confirmado is True

    cliente = Usuario.objects.get(email="cliente@teste.com")
    assert cliente.email_confirmado is True
    assert cliente.enderecos.filter(cidade="Medianeira", uf="PR", cep="85884-000").exists()


def test_popular_dados_executado_duas_vezes_nao_duplica_registros(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("popular_dados")
    call_command("popular_dados")

    assert Produto.objects.count() == 12
    assert Categoria.objects.count() == 3
    assert Usuario.objects.filter(email="admin@cupcakesgourmet.com").count() == 1
    assert Usuario.objects.filter(email="cliente@teste.com").count() == 1
    assert Pedido.objects.count() == 3


def test_senhas_de_admin_e_cliente_funcionam_no_login(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("popular_dados", senha_admin="SenhaDeTeste@2026")

    admin = authenticate(email="admin@cupcakesgourmet.com", password="SenhaDeTeste@2026")
    assert admin is not None
    assert admin.is_staff is True

    cliente = authenticate(email="cliente@teste.com", password="Cliente@123456")
    assert cliente is not None
    assert cliente.email_confirmado is True


def test_produtos_veganos_nao_mencionam_leite_ou_ovos_nos_ingredientes(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("popular_dados")

    produtos_veganos = Produto.objects.filter(categoria__slug="veganos")
    assert produtos_veganos.count() == 3

    for p in produtos_veganos:
        ingredientes_lower = p.ingredientes.lower()
        alergenicos_lower = p.alergenicos.lower()
        assert "leite" not in ingredientes_lower
        assert "ovo" not in ingredientes_lower
        assert "leite" not in alergenicos_lower
        assert "ovo" not in alergenicos_lower


def test_tres_pedidos_de_demonstracao_existem_com_status_esperados(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("popular_dados")

    cliente = Usuario.objects.get(email="cliente@teste.com")
    pedidos = list(Pedido.objects.filter(usuario=cliente).order_by("numero"))
    assert len(pedidos) == 3

    p_pix = Pedido.objects.get(usuario=cliente, numero="CG-DEMO-001")
    assert p_pix.status == "AGUARDANDO_PAGAMENTO"
    assert p_pix.forma_pagamento == "PIX"
    assert p_pix.estoque_baixado is False
    assert p_pix.itens.count() > 0
    assert p_pix.historico_status.filter(status="AGUARDANDO_PAGAMENTO").exists()

    p_prep = Pedido.objects.get(usuario=cliente, numero="CG-DEMO-002")
    assert p_prep.status == "EM_PREPARACAO"
    assert p_prep.forma_pagamento == "CARTAO"
    assert p_prep.estoque_baixado is True
    assert p_prep.itens.count() > 0
    assert p_prep.historico_status.filter(status="EM_PREPARACAO").exists()

    p_ent = Pedido.objects.get(usuario=cliente, numero="CG-DEMO-003")
    assert p_ent.status == "ENTREGUE"
    assert p_ent.forma_pagamento == "CARTAO"
    assert p_ent.estoque_baixado is True
    assert p_ent.itens.count() > 0
    assert p_ent.historico_status.filter(status="ENTREGUE").exists()
