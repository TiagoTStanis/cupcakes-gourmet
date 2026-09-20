from decimal import Decimal
import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from catalogo.models import Categoria, Produto
from catalogo.services import busca_service as servico
from catalogo.validators import validar_imagem

pytestmark = pytest.mark.django_db


def criar_imagem_valida(nome="teste.png", formato="PNG"):
    buffer = io.BytesIO()
    img = Image.new("RGB", (40, 40), color="pink")
    img.save(buffer, format=formato)
    buffer.seek(0)
    tipo_mime = "image/png" if formato.upper() == "PNG" else "image/jpeg"
    return SimpleUploadedFile(nome, buffer.read(), content_type=tipo_mime)


def test_soft_delete_oculta_da_listagem_e_mantem_no_banco(produtos_com_estoque, client):
    produto = produtos_com_estoque[0]
    total_antes = Produto.objects.count()

    produto.delete()

    assert Produto.objects.count() == total_antes
    produto.refresh_from_db()
    assert produto.ativo is False
    assert produto not in Produto.objects.ativos()

    resposta = client.get(reverse("catalogo:vitrine"))
    assert produto.nome not in resposta.content.decode()


def test_busca_por_limao_encontra_cupcake_com_e_sem_acento_e_caixa_alta(produtos_com_estoque, client):
    for termo in ["limao", "Limão", "LIMAO", "limão", "Siciliano"]:
        resultado = list(servico.buscar_produtos(termo))
        assert any("Limão Siciliano" in p.nome for p in resultado)

    resposta_busca = client.get(reverse("catalogo:busca"), {"q": "limao"})
    assert "Cupcake de Limão Siciliano" in resposta_busca.content.decode()

    resposta_api = client.get(reverse("catalogo:busca_api"), {"q": "Limão"})
    dados_api = resposta_api.json()
    nomes = [item["nome"] for item in dados_api["produtos"]]
    assert "Cupcake de Limão Siciliano" in nomes


def test_ordenacao_do_catalogo_por_total_vendas_padrao(produtos_com_estoque, client):
    resposta = client.get(reverse("catalogo:vitrine"))
    produtos_contexto = list(resposta.context["produtos"])
    vendas = [p.total_vendas for p in produtos_contexto]
    assert vendas == [120, 80, 45]


def test_ordenacao_do_catalogo_por_menor_e_maior_preco_e_nome(produtos_com_estoque, client):
    resp_menor = client.get(reverse("catalogo:vitrine"), {"ordenacao": "menor_preco"})
    precos_menor = [p.preco for p in resp_menor.context["produtos"]]
    assert precos_menor == [Decimal("11.00"), Decimal("12.50"), Decimal("14.00")]

    resp_maior = client.get(reverse("catalogo:vitrine"), {"ordenacao": "maior_preco"})
    precos_maior = [p.preco for p in resp_maior.context["produtos"]]
    assert precos_maior == [Decimal("14.00"), Decimal("12.50"), Decimal("11.00")]

    resp_nome = client.get(reverse("catalogo:vitrine"), {"ordenacao": "nome"})
    nomes = [p.nome for p in resp_nome.context["produtos"]]
    assert nomes == sorted(nomes)


def test_filtro_por_categoria(produtos_com_estoque, client):
    resposta = client.get(reverse("catalogo:vitrine"), {"categoria": "veganos"})
    produtos = list(resposta.context["produtos"])
    assert len(produtos) == 1
    assert produtos[0].slug == "cupcake-vegano-frutas-vermelhas"

    conteudo = resposta.content.decode()
    assert "Cupcake Vegano de Frutas Vermelhas" in conteudo
    assert "Cupcake de Chocolate Belga" not in conteudo


def test_categoria_sem_produtos_mostra_aviso_especifico(categorias, client):
    resposta = client.get(reverse("catalogo:vitrine"), {"categoria": "tematicos"})
    conteudo = resposta.content.decode()
    assert "Nenhum cupcake disponivel nesta categoria por enquanto." in conteudo or "Nenhum cupcake disponível nesta categoria por enquanto." in conteudo


def test_vitrine_sem_produtos_mostra_mensagem_padrao(db, client):
    resposta = client.get(reverse("catalogo:vitrine"))
    assert "Em breve traremos novidades!" in resposta.content.decode()


def test_produto_inativo_ou_inexistente_retorna_404(produtos_com_estoque, client):
    produto = produtos_com_estoque[0]
    produto.ativo = False
    produto.save()

    resp_inativo = client.get(reverse("catalogo:produto_detalhe", kwargs={"slug": produto.slug}))
    assert resp_inativo.status_code == 404

    resp_inexistente = client.get(reverse("catalogo:produto_detalhe", kwargs={"slug": "sabor-que-nao-existe"}))
    assert resp_inexistente.status_code == 404


def test_produto_em_categoria_inativa_retorna_404(produtos_com_estoque, client):
    produto = produtos_com_estoque[0]
    produto.categoria.ativa = False
    produto.categoria.save()

    resp = client.get(reverse("catalogo:produto_detalhe", kwargs={"slug": produto.slug}))
    assert resp.status_code == 404


def test_botao_compra_desabilitado_quando_estoque_zerado(produtos_com_estoque, client):
    produto = produtos_com_estoque[0]
    produto.estoque = 0
    produto.save()

    resposta = client.get(reverse("catalogo:produto_detalhe", kwargs={"slug": produto.slug}))
    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert "disabled" in conteudo
    assert "Indisponivel no momento" in conteudo or "Indisponível no momento" in conteudo


def test_botao_compra_habilitado_quando_ha_estoque(produtos_com_estoque, client):
    produto = produtos_com_estoque[0]
    produto.estoque = 5
    produto.save()

    resposta = client.get(reverse("catalogo:produto_detalhe", kwargs={"slug": produto.slug}))
    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert "Adicionar ao carrinho" in conteudo


def test_detalhes_exibe_ingredientes_e_banner_alergenicos(produtos_com_estoque, client):
    produto = produtos_com_estoque[0]
    resposta = client.get(reverse("catalogo:produto_detalhe", kwargs={"slug": produto.slug}))
    conteudo = resposta.content.decode()
    assert produto.ingredientes in conteudo
    assert produto.alergenicos in conteudo
    assert "alergenicos" in conteudo


def test_busca_sem_resultados_mostra_mensagem_especifica(client):
    resposta = client.get(reverse("catalogo:busca"), {"q": "sabor_inexistente_123"})
    conteudo = resposta.content.decode()
    assert "Nenhum cupcake encontrado para 'sabor_inexistente_123'." in conteudo


def test_endpoint_api_busca_retorna_json_correto(produtos_com_estoque, client):
    resposta = client.get(reverse("catalogo:busca_api"), {"q": "chocolate"})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["total"] == 1
    assert dados["produtos"][0]["slug"] == "cupcake-de-chocolate-belga"
    assert "R$ 12,50" in dados["produtos"][0]["preco_formatado"]


def test_validador_imagem_rejeita_arquivo_que_nao_e_imagem():
    falso = SimpleUploadedFile("teste.png", b"conteudo invalido de texto", content_type="image/png")
    with pytest.raises(ValidationError, match="não é uma imagem válida"):
        validar_imagem(falso)


def test_validador_imagem_rejeita_extensao_invalida():
    arquivo_pdf = SimpleUploadedFile("manual.pdf", b"%PDF-1.4", content_type="application/pdf")
    with pytest.raises(ValidationError, match="Extensão inválida"):
        validar_imagem(arquivo_pdf)


def test_validador_imagem_rejeita_arquivo_acima_de_5mb():
    cinco_mb_e_um = 5 * 1024 * 1024 + 1
    arquivo_pesado = SimpleUploadedFile("foto.jpg", b"0" * cinco_mb_e_um, content_type="image/jpeg")
    with pytest.raises(ValidationError, match="no máximo 5MB"):
        validar_imagem(arquivo_pesado)


def test_validador_imagem_aceita_png_e_jpg_validos():
    arquivo_png = criar_imagem_valida("doce.png", "PNG")
    arquivo_jpg = criar_imagem_valida("doce.jpg", "JPEG")
    validar_imagem(arquivo_png)
    validar_imagem(arquivo_jpg)
