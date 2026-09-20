from django.db.models import Sum

from carrinho.services import carrinho_service
from pedidos.models import Pedido


def listar_pedidos(usuario):
    return (
        Pedido.objects.filter(usuario=usuario)
        .annotate(total_itens=Sum("itens__quantidade"))
        .order_by("-criado_em", "-pk")
        .prefetch_related("itens__produto")
    )


def repetir_pedido(usuario, pedido):
    carrinho = carrinho_service.obter_carrinho(usuario)
    adicionados = []
    erros = []

    for item in pedido.itens.select_related("produto", "produto__categoria").all():
        produto = item.produto
        if not produto or not produto.ativo or (hasattr(produto, "categoria") and not produto.categoria.ativa):
            erros.append(f"{item.nome_produto} não está mais disponível.")
            continue

        try:
            carrinho_service.adicionar(carrinho, produto, quantidade=item.quantidade)
            adicionados.append(item.nome_produto)
        except carrinho_service.ErroCarrinho as erro:
            texto_erro = str(erro)
            if "não está mais disponível" in texto_erro:
                erros.append(f"{item.nome_produto} não está mais disponível.")
            else:
                erros.append(f"{item.nome_produto}: {texto_erro}")

    return adicionados, erros
