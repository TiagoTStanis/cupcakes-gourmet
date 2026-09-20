from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from catalogo.models import Produto
from carrinho.models import Carrinho, ItemCarrinho
from pedidos.services.estoque_service import estoque_disponivel, liberar_do_usuario


class ErroCarrinho(Exception):
    pass


def obter_carrinho(usuario):
    if not usuario or not usuario.is_authenticated:
        raise ErroCarrinho("Entre na sua conta para acessar o carrinho.")

    carrinho, criado = Carrinho.objects.get_or_create(usuario=usuario)

    if not criado and carrinho.atualizado_em:
        # Quando passam mais de 24h desde a última interação, zera os itens
        if timezone.now() - carrinho.atualizado_em > timedelta(hours=24):
            carrinho.itens.all().delete()
            liberar_do_usuario(carrinho.usuario)
            carrinho.save()

    return carrinho


def _resolver_carrinho(carrinho_ou_usuario):
    if isinstance(carrinho_ou_usuario, Carrinho):
        return carrinho_ou_usuario
    return obter_carrinho(carrinho_ou_usuario)


def _resolver_produto(produto_ou_id):
    if isinstance(produto_ou_id, Produto):
        return produto_ou_id
    try:
        return Produto.objects.get(pk=produto_ou_id)
    except Produto.DoesNotExist:
        raise ErroCarrinho("Cupcake não encontrado.")


def adicionar(carrinho_ou_usuario, produto_ou_id, quantidade=1):
    carrinho = _resolver_carrinho(carrinho_ou_usuario)
    produto = _resolver_produto(produto_ou_id)

    try:
        quantidade = int(quantidade)
    except (ValueError, TypeError):
        raise ErroCarrinho("Quantidade inválida.")

    if quantidade <= 0:
        raise ErroCarrinho("A quantidade deve ser de pelo menos 1 unidade.")

    if not produto.ativo or (hasattr(produto, "categoria") and not produto.categoria.ativa):
        raise ErroCarrinho("Este cupcake não está mais disponível.")

    disponivel = estoque_disponivel(produto, ignorar_usuario=carrinho.usuario)
    if disponivel <= 0:
        raise ErroCarrinho("Produto sem estoque disponível no momento.")

    item = carrinho.itens.filter(produto=produto).first()
    quantidade_atual = item.quantidade if item else 0
    nova_quantidade = quantidade_atual + quantidade

    if nova_quantidade > 10:
        raise ErroCarrinho("Você pode levar no máximo 10 unidades de cada cupcake.")

    if nova_quantidade > disponivel:
        raise ErroCarrinho(f"Só temos {disponivel} unidades disponíveis.")

    if item:
        item.quantidade = nova_quantidade
        item.save(update_fields=["quantidade"])
    else:
        item = ItemCarrinho.objects.create(
            carrinho=carrinho,
            produto=produto,
            quantidade=nova_quantidade,
        )

    liberar_do_usuario(carrinho.usuario)
    carrinho.save()
    return item


def alterar_quantidade(carrinho_ou_usuario, produto_ou_id, quantidade):
    carrinho = _resolver_carrinho(carrinho_ou_usuario)
    produto = _resolver_produto(produto_ou_id)

    try:
        quantidade = int(quantidade)
    except (ValueError, TypeError):
        raise ErroCarrinho("Quantidade inválida.")

    if quantidade < 0:
        raise ErroCarrinho("Quantidade não pode ser negativa.")

    if quantidade == 0:
        carrinho.itens.filter(produto=produto).delete()
        liberar_do_usuario(carrinho.usuario)
        carrinho.save()
        return None

    if not produto.ativo or (hasattr(produto, "categoria") and not produto.categoria.ativa):
        raise ErroCarrinho("Este cupcake não está mais disponível.")

    if quantidade > 10:
        raise ErroCarrinho("Você pode levar no máximo 10 unidades de cada cupcake.")

    disponivel = estoque_disponivel(produto, ignorar_usuario=carrinho.usuario)
    if quantidade > disponivel:
        raise ErroCarrinho(f"Só temos {disponivel} unidades disponíveis.")

    item, _ = ItemCarrinho.objects.get_or_create(
        carrinho=carrinho,
        produto=produto,
        defaults={"quantidade": quantidade},
    )
    if item.quantidade != quantidade:
        item.quantidade = quantidade
        item.save(update_fields=["quantidade"])

    liberar_do_usuario(carrinho.usuario)
    carrinho.save()
    return item


def remover(carrinho_ou_usuario, produto_ou_id):
    carrinho = _resolver_carrinho(carrinho_ou_usuario)
    produto = _resolver_produto(produto_ou_id)

    carrinho.itens.filter(produto=produto).delete()
    liberar_do_usuario(carrinho.usuario)
    carrinho.save()
    return carrinho


def limpar_carrinho(carrinho_ou_usuario):
    carrinho = _resolver_carrinho(carrinho_ou_usuario)
    carrinho.itens.all().delete()
    liberar_do_usuario(carrinho.usuario)
    carrinho.save()
    return carrinho


def calcular_totais(carrinho_ou_usuario):
    carrinho = _resolver_carrinho(carrinho_ou_usuario)
    itens = list(carrinho.itens.select_related("produto"))
    quantidade_total = sum(item.quantidade for item in itens)
    total_geral = sum((item.subtotal for item in itens), Decimal("0.00"))
    return {
        "itens": itens,
        "quantidade_total": quantidade_total,
        "total_geral": total_geral,
    }
