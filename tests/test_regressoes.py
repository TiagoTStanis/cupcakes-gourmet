from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from pedidos.models import Pedido
from pedidos.services import pedido_service
from pedidos.services.estoque_service import ErroEstoque
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def _pedido_pix(usuario, numero, expira_em):
    return Pedido.objects.create(
        numero=numero,
        usuario=usuario,
        endereco_entrega="Rua das Flores, 123\nCentro - Medianeira/PR",
        subtotal=Decimal("25.00"),
        valor_frete=Decimal("8.00"),
        valor_total=Decimal("33.00"),
        forma_pagamento="PIX",
        status="AGUARDANDO_PAGAMENTO",
        pix_expira_em=expira_em,
    )


def test_preco_zero_ou_negativo_e_rejeitado(produtos_com_estoque):
    produto = produtos_com_estoque[0]
    for valor in ("-5.00", "0.00"):
        produto.preco = Decimal(valor)
        with pytest.raises(ValidationError) as erro:
            produto.full_clean()
        assert "preco" in erro.value.message_dict


def test_popular_dados_usa_a_senha_informada_para_o_administrador(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("popular_dados", senha_admin="Outra@Senha1", stdout=open(tmp_path / "saida.txt", "w"))
    assert authenticate(email="admin@cupcakesgourmet.com", password="Outra@Senha1") is not None
    assert authenticate(email="admin@cupcakesgourmet.com", password="SenhaAntiga@1") is None


def test_popular_dados_nao_redefine_senha_de_conta_existente(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    Usuario.objects.create_superuser(
        email="admin@cupcakesgourmet.com", password="Trocada@999", nome_completo="Administrador"
    )
    call_command("popular_dados", stdout=open(tmp_path / "saida.txt", "w"))
    assert authenticate(email="admin@cupcakesgourmet.com", password="Trocada@999") is not None


def test_pix_vencido_e_cancelado_ao_listar(usuario_cliente):
    vencido = _pedido_pix(usuario_cliente, "CG-VENC-01", timezone.now() - timedelta(minutes=1))
    valido = _pedido_pix(usuario_cliente, "CG-VALI-01", timezone.now() + timedelta(minutes=20))
    pedido_service.cancelar_pix_vencidos()
    vencido.refresh_from_db()
    valido.refresh_from_db()
    assert vencido.status == "CANCELADO"
    assert valido.status == "AGUARDANDO_PAGAMENTO"


def test_historico_mostra_pix_vencido_como_cancelado(client, usuario_cliente):
    pedido = _pedido_pix(usuario_cliente, "CG-VENC-02", timezone.now() - timedelta(minutes=5))
    client.force_login(usuario_cliente)
    resposta = client.get(reverse("pedidos:historico"))
    assert resposta.status_code == 200
    pedido.refresh_from_db()
    assert pedido.status == "CANCELADO"


def test_painel_trata_falta_de_estoque_ao_avancar_status(client, usuario_staff, usuario_cliente, monkeypatch):
    pedido = _pedido_pix(usuario_cliente, "CG-EST-01", timezone.now() + timedelta(minutes=20))

    def falhar(*args, **kwargs):
        raise ErroEstoque()

    monkeypatch.setattr(pedido_service, "alterar_status", falhar)
    client.force_login(usuario_staff)
    resposta = client.post(reverse("painel:pedido_avancar_status", args=[pedido.numero]))
    assert resposta.status_code == 302
    pedido.refresh_from_db()
    assert pedido.status == "AGUARDANDO_PAGAMENTO"


def test_busca_js_escapa_o_texto_antes_de_inserir_no_html():
    conteudo = open("static/js/busca.js", encoding="utf-8").read()
    assert "escaparHtml" in conteudo
    assert "mensagemVazio.innerHTML" not in conteudo


def test_popular_dados_gera_senha_aleatoria_quando_nao_recebe_nenhuma(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    saida = tmp_path / "saida.txt"
    with open(saida, "w") as arquivo:
        call_command("popular_dados", stdout=arquivo)
    texto = saida.read_text()
    assert "senha gerada:" in texto
    senha = texto.split("senha gerada: ")[1].split(" ")[0]
    assert len(senha) >= 12
    assert authenticate(email="admin@cupcakesgourmet.com", password=senha) is not None


def test_popular_dados_nao_anuncia_senha_de_admin_que_ja_existia(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    Usuario.objects.create_superuser(
        email="admin@cupcakesgourmet.com", password="Existente@123", nome_completo="Administrador"
    )
    saida = tmp_path / "saida.txt"
    with open(saida, "w") as arquivo:
        call_command("popular_dados", stdout=arquivo)
    assert "senha gerada" not in saida.read_text()
    assert authenticate(email="admin@cupcakesgourmet.com", password="Existente@123") is not None
