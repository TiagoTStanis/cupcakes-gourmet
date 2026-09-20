from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests
from django.urls import reverse
from django.utils import timezone

from carrinho.services import carrinho_service
from pedidos.models import Cupom, TabelaFreteUF
from pedidos.services import cupom_service, frete_service, resumo_service
from pedidos.services.cupom_service import ErroCupom
from pedidos.services.frete_service import ErroFrete
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def test_frete_gratis_em_150_01_e_nao_em_150_00(tabela_frete):
    # Exatamente R$ 150,00 não confere frete grátis
    resultado_150 = frete_service.calcular_frete("PR", Decimal("150.00"))
    assert resultado_150["gratis"] is False
    assert resultado_150["valor"] == Decimal("8.00")

    # A partir de R$ 150,01 o frete é isento (grátis)
    resultado_150_01 = frete_service.calcular_frete("PR", Decimal("150.01"))
    assert resultado_150_01["gratis"] is True
    assert resultado_150_01["valor"] == Decimal("0.00")

    # Valor inferior continua cobrando tabela normal
    resultado_abaixo = frete_service.calcular_frete("SP", Decimal("149.99"))
    assert resultado_abaixo["gratis"] is False
    assert resultado_abaixo["valor"] == Decimal("14.00")


def test_frete_gratis_considera_subtotal_apos_cupom(tabela_frete, usuario_cliente):
    # R$ 160,00 com cupom de 10% resulta em R$ 144,00 (não atinge R$ 150,01)
    cupom = Cupom.objects.create(
        codigo="DEZ10",
        tipo="PERCENTUAL",
        valor=Decimal("10.00"),
        valor_minimo_pedido=Decimal("0.00"),
        data_validade=timezone.now() + timedelta(days=2),
        ativo=True,
    )
    subtotal_160 = Decimal("160.00")
    desconto = cupom_service.calcular_desconto(cupom, subtotal_160)
    subtotal_liquido = subtotal_160 - desconto
    assert subtotal_liquido == Decimal("144.00")

    resultado_frete = frete_service.calcular_frete("SP", subtotal_apos_desconto=subtotal_liquido)
    assert resultado_frete["gratis"] is False
    assert resultado_frete["valor"] == Decimal("14.00")

    # R$ 170,00 com cupom de 10% resulta em R$ 153,00 (supera R$ 150,00, portanto frete grátis)
    subtotal_170 = Decimal("170.00")
    desconto_170 = cupom_service.calcular_desconto(cupom, subtotal_170)
    subtotal_liquido_170 = subtotal_170 - desconto_170
    assert subtotal_liquido_170 == Decimal("153.00")

    resultado_frete_gratis = frete_service.calcular_frete("SP", subtotal_apos_desconto=subtotal_liquido_170)
    assert resultado_frete_gratis["gratis"] is True
    assert resultado_frete_gratis["valor"] == Decimal("0.00")


def test_uf_fora_da_tabela(tabela_frete):
    with pytest.raises(ErroFrete) as erro:
        frete_service.calcular_frete("BA")
    mensagem = str(erro.value)
    assert "Infelizmente não entregamos neste endereço ainda." in mensagem or "Infelizmente nao entregamos neste endereco ainda." in mensagem


def test_cep_invalido_formato_e_retorno_viacep():
    formatos_invalidos = ["123", "800000000", "8000-000", "abc", ""]
    for formato in formatos_invalidos:
        with pytest.raises(ErroFrete) as erro:
            frete_service.normalizar_cep(formato)
        assert "CEP inválido" in str(erro.value) or "CEP invalido" in str(erro.value)

    resposta_mock = Mock()
    resposta_mock.raise_for_status.return_value = None
    resposta_mock.json.return_value = {"erro": True}

    with patch("requests.get", return_value=resposta_mock):
        with pytest.raises(ErroFrete) as erro_viacep:
            frete_service.consultar_cep("99999-999")
        assert "CEP inválido" in str(erro_viacep.value) or "CEP invalido" in str(erro_viacep.value)


def test_falha_de_rede_do_viacep():
    with patch("requests.get", side_effect=requests.RequestException("Falha na rede")):
        with pytest.raises(ErroFrete) as erro:
            frete_service.consultar_cep("80010-000")
        assert "Não foi possível consultar o CEP no momento" in str(erro.value) or "Nao foi possivel consultar o CEP no momento" in str(erro.value)


def test_cupom_vencido_recusado(usuario_cliente):
    Cupom.objects.create(
        codigo="VENCIDO",
        tipo="PERCENTUAL",
        valor=Decimal("10.00"),
        valor_minimo_pedido=Decimal("0.00"),
        data_validade=timezone.now() - timedelta(days=1),
        ativo=True,
    )
    with pytest.raises(ErroCupom) as erro:
        cupom_service.validar_cupom("VENCIDO", usuario_cliente, Decimal("50.00"))
    assert "Este cupom não está mais disponível" in str(erro.value) or "Este cupom nao esta mais disponivel" in str(erro.value)


def test_cupom_inativo_recusado(usuario_cliente):
    Cupom.objects.create(
        codigo="DESATIVADO",
        tipo="FIXO",
        valor=Decimal("5.00"),
        valor_minimo_pedido=Decimal("0.00"),
        data_validade=timezone.now() + timedelta(days=5),
        ativo=False,
    )
    with pytest.raises(ErroCupom) as erro:
        cupom_service.validar_cupom("DESATIVADO", usuario_cliente, Decimal("50.00"))
    assert "Este cupom não está mais disponível" in str(erro.value) or "Este cupom nao esta mais disponivel" in str(erro.value)


def test_cupom_abaixo_do_valor_minimo(usuario_cliente):
    Cupom.objects.create(
        codigo="MINIMO50",
        tipo="FIXO",
        valor=Decimal("10.00"),
        valor_minimo_pedido=Decimal("50.00"),
        data_validade=timezone.now() + timedelta(days=5),
        ativo=True,
    )
    with pytest.raises(ErroCupom) as erro:
        cupom_service.validar_cupom("MINIMO50", usuario_cliente, Decimal("49.99"))
    mensagem = str(erro.value)
    assert "50,00" in mensagem
    assert "acima de R$" in mensagem


def test_cupom_reutilizado_pelo_mesmo_usuario_e_permitido_para_outro(cupom_valido, usuario_cliente):
    outro_usuario = Usuario.objects.create_user(
        "outro@teste.com",
        "Outro@123456",
        nome_completo="Outro Cliente",
        email_confirmado=True,
    )

    cupom_service.registrar_uso(cupom_valido, usuario_cliente)

    with pytest.raises(ErroCupom) as erro:
        cupom_service.validar_cupom(cupom_valido.codigo, usuario_cliente, Decimal("50.00"))
    mensagem = str(erro.value)
    assert "Você já usou este cupom em um pedido anterior." in mensagem or "Voce ja usou este cupom em um pedido anterior." in mensagem

    cupom_liberado = cupom_service.validar_cupom(cupom_valido.codigo, outro_usuario, Decimal("50.00"))
    assert cupom_liberado.id == cupom_valido.id


def test_calculo_desconto_percentual_e_fixo():
    cupom_perc = Cupom(tipo="PERCENTUAL", valor=Decimal("15.00"))
    desconto_perc = cupom_service.calcular_desconto(cupom_perc, Decimal("80.00"))
    assert desconto_perc == Decimal("12.00")

    cupom_fixo = Cupom(tipo="FIXO", valor=Decimal("25.00"))
    desconto_fixo = cupom_service.calcular_desconto(cupom_fixo, Decimal("100.00"))
    assert desconto_fixo == Decimal("25.00")

    desconto_limitado = cupom_service.calcular_desconto(cupom_fixo, Decimal("20.00"))
    assert desconto_limitado == Decimal("20.00")


def test_desconto_nao_incide_no_frete(tabela_frete, usuario_cliente):
    cupom = Cupom.objects.create(
        codigo="DESCONTO15",
        tipo="FIXO",
        valor=Decimal("15.00"),
        valor_minimo_pedido=Decimal("20.00"),
        data_validade=timezone.now() + timedelta(days=3),
        ativo=True,
    )
    subtotal = Decimal("50.00")
    desconto = cupom_service.calcular_desconto(cupom, subtotal)
    subtotal_com_desconto = subtotal - desconto
    assert subtotal_com_desconto == Decimal("35.00")

    # O frete para SP na tabela é R$ 14,00 e permanece inalterado
    info_frete = frete_service.calcular_frete("SP", subtotal_apos_desconto=subtotal_com_desconto)
    assert info_frete["valor"] == Decimal("14.00")
    assert subtotal_com_desconto + info_frete["valor"] == Decimal("49.00")


def test_endpoints_exigem_login(client):
    rotas_post = [
        reverse("pedidos:consultar_cep"),
        reverse("pedidos:aplicar_cupom"),
        reverse("pedidos:remover_cupom"),
    ]
    for rota in rotas_post:
        resposta = client.post(rota, {})
        assert resposta.status_code == 401
        dados = resposta.json()
        assert dados["sucesso"] is False

    resposta_get = client.get(reverse("pedidos:resumo"))
    assert resposta_get.status_code == 401
    dados_get = resposta_get.json()
    assert dados_get["sucesso"] is False


def test_total_do_resumo_correto_com_decimal(tabela_frete, usuario_cliente, produtos_com_estoque, cupom_valido):
    carrinho = carrinho_service.obter_carrinho(usuario_cliente)
    carrinho_service.adicionar(carrinho, produtos_com_estoque[0], quantidade=2)  # 2 x 12.50 = 25.00
    carrinho_service.adicionar(carrinho, produtos_com_estoque[1], quantidade=1)  # 1 x 11.00 = 11.00
    # Subtotal total: 36.00

    # Cupom de 10%: desconto de R$ 3,60 -> subtotal líquido R$ 32,40
    # Frete para PR: R$ 8,00 -> Total esperado: R$ 40,40
    sessao_mock = {
        "cupom_codigo": cupom_valido.codigo,
        "frete_cep": "80010-000",
        "frete_uf": "PR",
    }
    resumo = resumo_service.obter_resumo_carrinho(
        usuario_cliente,
        carrinho=carrinho,
        sessao=sessao_mock,
    )

    assert isinstance(resumo["subtotal"], Decimal)
    assert resumo["subtotal"] == Decimal("36.00")
    assert isinstance(resumo["desconto"], Decimal)
    assert resumo["desconto"] == Decimal("3.60")
    assert isinstance(resumo["frete"], Decimal)
    assert resumo["frete"] == Decimal("8.00")
    assert isinstance(resumo["total"], Decimal)
    assert resumo["total"] == Decimal("40.40")
    assert resumo["frete_gratis"] is False


def test_views_consultar_cep_com_mock_viacep_e_sessao(tabela_frete, usuario_cliente, client, carrinho_com_itens):
    client.force_login(usuario_cliente)

    mock_resp = Mock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "cep": "80010-000",
        "logradouro": "Rua XV de Novembro",
        "bairro": "Centro",
        "localidade": "Curitiba",
        "uf": "PR",
    }

    with patch("requests.get", return_value=mock_resp):
        resposta = client.post(
            reverse("pedidos:consultar_cep"),
            {"cep": "80010-000"},
        )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["sucesso"] is True
    assert dados["endereco"]["uf"] == "PR"
    assert dados["frete"]["valor"] == "8.00"
    assert dados["frete"]["prazo_dias"] == 2

    # Verifica persistência na sessão
    sessao = client.session
    assert sessao.get("frete_cep") == "80010-000"
    assert sessao.get("frete_uf") == "PR"


def test_views_aplicar_e_remover_cupom(usuario_cliente, client, carrinho_com_itens, cupom_valido):
    client.force_login(usuario_cliente)

    resposta_aplicar = client.post(
        reverse("pedidos:aplicar_cupom"),
        {"codigo": cupom_valido.codigo},
    )
    assert resposta_aplicar.status_code == 200
    dados_app = resposta_aplicar.json()
    assert dados_app["sucesso"] is True
    assert dados_app["cupom"]["codigo"] == cupom_valido.codigo
    assert client.session.get("cupom_codigo") == cupom_valido.codigo

    resposta_remover = client.post(reverse("pedidos:remover_cupom"))
    assert resposta_remover.status_code == 200
    dados_rem = resposta_remover.json()
    assert dados_rem["sucesso"] is True
    assert client.session.get("cupom_codigo") is None

    resposta_resumo = client.get(reverse("pedidos:resumo"))
    assert resposta_resumo.status_code == 200
    assert resposta_resumo.json()["resumo"]["desconto"] == "0.00"


def test_views_retornam_status_400_para_erros(usuario_cliente, client):
    client.force_login(usuario_cliente)

    resposta_cep = client.post(reverse("pedidos:consultar_cep"), {"cep": ""})
    assert resposta_cep.status_code == 400
    assert resposta_cep.json()["sucesso"] is False

    resposta_cupom = client.post(reverse("pedidos:aplicar_cupom"), {"codigo": "INEXISTENTE"})
    assert resposta_cupom.status_code == 400
    assert resposta_cupom.json()["sucesso"] is False
