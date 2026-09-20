from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from catalogo.models import Categoria, Produto
from catalogo.services.busca_service import (
    buscar_produtos,
    listar_categorias_ativas,
    listar_produtos,
)


def vitrine(request):
    categoria_slug = request.GET.get("categoria", "").strip()
    ordenacao = request.GET.get("ordenacao", "popularidade").strip()

    categorias = listar_categorias_ativas()
    produtos = listar_produtos(categoria_slug=categoria_slug, ordenacao=ordenacao)

    categoria_selecionada = None
    if categoria_slug:
        categoria_selecionada = Categoria.objects.filter(slug=categoria_slug, ativa=True).first()

    contexto = {
        "categorias": categorias,
        "produtos": produtos,
        "categoria_ativa": categoria_slug,
        "categoria_selecionada": categoria_selecionada,
        "ordenacao_atual": ordenacao,
    }
    return render(request, "catalogo/vitrine.html", contexto)


def busca(request):
    termo = request.GET.get("q", "").strip()
    buscou = "q" in request.GET
    produtos = buscar_produtos(termo=termo) if buscou else []

    contexto = {
        "termo": termo,
        "produtos": produtos,
        "buscou": buscou,
    }
    return render(request, "catalogo/busca.html", contexto)


def busca_api(request):
    termo = request.GET.get("q", "").strip()
    produtos = buscar_produtos(termo=termo)
    dados = [
        {
            "id": p.id,
            "nome": p.nome,
            "slug": p.slug,
            "preco": str(p.preco),
            "preco_formatado": f"R$ {p.preco:.2f}".replace(".", ","),
            "imagem_url": p.imagem.url if p.imagem else "",
            "categoria": p.categoria.nome,
            "url": p.get_absolute_url(),
            "estoque": p.estoque,
        }
        for p in produtos
    ]
    return JsonResponse({"produtos": dados, "total": len(dados), "termo": termo})


def produto_detalhe(request, slug):
    produto = get_object_or_404(
        Produto.objects.ativos().select_related("categoria"),
        slug=slug,
        categoria__ativa=True,
    )
    return render(request, "catalogo/detalhe.html", {"produto": produto})
