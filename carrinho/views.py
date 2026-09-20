import json
from decimal import Decimal
from urllib.parse import quote

from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalogo.models import Produto
from carrinho.services import carrinho_service as servico
from carrinho.services.carrinho_service import ErroCarrinho


def _extrair_dados(request):
    if request.content_type == "application/json" and request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST


def _tratar_visitante(request):
    messages.info(request, "Entre na sua conta para adicionar itens ao carrinho.")
    proxima = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER") or request.path
    return redirect(f"{reverse('usuarios:login')}?next={quote(proxima, safe='/')}")


def carrinho_detalhe(request):
    if not request.user.is_authenticated:
        return _tratar_visitante(request)

    carrinho = servico.obter_carrinho(request.user)
    totais = servico.calcular_totais(carrinho)

    contexto = {
        "carrinho": carrinho,
        "itens": totais["itens"],
        "total_geral": totais["total_geral"],
        "quantidade_total": totais["quantidade_total"],
    }
    return render(request, "carrinho/detalhe.html", contexto)


@require_POST
def adicionar_item(request):
    if not request.user.is_authenticated:
        return _tratar_visitante(request)

    dados = _extrair_dados(request)
    produto_id = dados.get("produto_id")
    quantidade = dados.get("quantidade", 1)

    if not produto_id:
        return JsonResponse({"sucesso": False, "erro": "Produto não informado."}, status=400)

    try:
        produto = Produto.objects.get(pk=produto_id)
    except Produto.DoesNotExist:
        return JsonResponse({"sucesso": False, "erro": "Cupcake não encontrado."}, status=404)

    try:
        item = servico.adicionar(request.user, produto, quantidade=quantidade)
        carrinho = servico.obter_carrinho(request.user)
        totais = servico.calcular_totais(carrinho)

        return JsonResponse({
            "sucesso": True,
            "mensagem": f"{produto.nome} adicionado ao carrinho.",
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "quantidade": item.quantidade,
            "subtotal_item": f"{item.subtotal:.2f}",
            "subtotal_item_formatado": f"R$ {item.subtotal:.2f}".replace(".", ","),
            "total_geral": f"{totais['total_geral']:.2f}",
            "total_geral_formatado": f"R$ {totais['total_geral']:.2f}".replace(".", ","),
            "quantidade_total": totais["quantidade_total"],
        })
    except ErroCarrinho as erro:
        return JsonResponse({"sucesso": False, "erro": str(erro)}, status=400)


@require_POST
def alterar_quantidade_item(request):
    if not request.user.is_authenticated:
        return _tratar_visitante(request)

    dados = _extrair_dados(request)
    produto_id = dados.get("produto_id")
    quantidade = dados.get("quantidade")

    if produto_id is None or quantidade is None:
        return JsonResponse({"sucesso": False, "erro": "Dados incompletos para alteração."}, status=400)

    try:
        produto = Produto.objects.get(pk=produto_id)
    except Produto.DoesNotExist:
        return JsonResponse({"sucesso": False, "erro": "Cupcake não encontrado."}, status=404)

    try:
        item = servico.alterar_quantidade(request.user, produto, quantidade=quantidade)
        carrinho = servico.obter_carrinho(request.user)
        totais = servico.calcular_totais(carrinho)

        subtotal = item.subtotal if item else Decimal("0.00")
        qtd = item.quantidade if item else 0

        return JsonResponse({
            "sucesso": True,
            "removido": item is None,
            "produto_id": produto.id,
            "quantidade": qtd,
            "subtotal_item": f"{subtotal:.2f}",
            "subtotal_item_formatado": f"R$ {subtotal:.2f}".replace(".", ","),
            "total_geral": f"{totais['total_geral']:.2f}",
            "total_geral_formatado": f"R$ {totais['total_geral']:.2f}".replace(".", ","),
            "quantidade_total": totais["quantidade_total"],
        })
    except ErroCarrinho as erro:
        return JsonResponse({"sucesso": False, "erro": str(erro)}, status=400)


@require_POST
def remover_item(request, produto_id=None):
    if not request.user.is_authenticated:
        return _tratar_visitante(request)

    if produto_id is None:
        dados = _extrair_dados(request)
        produto_id = dados.get("produto_id")

    if not produto_id:
        return JsonResponse({"sucesso": False, "erro": "Produto não informado para remoção."}, status=400)

    try:
        produto = Produto.objects.get(pk=produto_id)
    except Produto.DoesNotExist:
        return JsonResponse({"sucesso": False, "erro": "Cupcake não encontrado."}, status=404)

    try:
        carrinho = servico.remover(request.user, produto)
        totais = servico.calcular_totais(carrinho)

        return JsonResponse({
            "sucesso": True,
            "removido": True,
            "produto_id": produto.id,
            "quantidade": 0,
            "subtotal_item": "0.00",
            "subtotal_item_formatado": "R$ 0,00",
            "total_geral": f"{totais['total_geral']:.2f}",
            "total_geral_formatado": f"R$ {totais['total_geral']:.2f}".replace(".", ","),
            "quantidade_total": totais["quantidade_total"],
        })
    except ErroCarrinho as erro:
        return JsonResponse({"sucesso": False, "erro": str(erro)}, status=400)
