from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from catalogo.models import Produto
from pedidos.models import Pedido, ReservaEstoque
from usuarios.models import Usuario


class ErroEstoque(Exception):
    def __init__(self):
        super().__init__("Um dos itens ficou indisponível. Revise seu carrinho.")


def liberar_expiradas():
    return ReservaEstoque.objects.filter(ativa=True, expira_em__lte=timezone.now()).update(ativa=False)


def liberar_do_usuario(usuario):
    reservas = ReservaEstoque.objects.filter(usuario=usuario, ativa=True)
    # Alterar um novo carrinho não libera unidades de um PIX ainda válido.
    prazos_pix = Pedido.objects.filter(
        usuario=usuario, forma_pagamento="PIX", status="AGUARDANDO_PAGAMENTO",
        pix_expira_em__gt=timezone.now(),
    ).values("pix_expira_em")
    return reservas.exclude(expira_em__in=prazos_pix).update(ativa=False)


def estoque_disponivel(produto, ignorar_usuario=None):
    liberar_expiradas()
    reservas = ReservaEstoque.objects.filter(produto=produto, ativa=True, expira_em__gt=timezone.now())
    if ignorar_usuario is not None:
        reservas = reservas.exclude(usuario=ignorar_usuario)
    reservado = reservas.aggregate(total=Sum("quantidade"))["total"] or 0
    estoque = Produto.objects.values_list("estoque", flat=True).get(pk=produto.pk)
    return max(0, estoque - reservado)


def _quantidades(itens):
    quantidades = {}
    for item in itens:
        if item.quantidade <= 0:
            raise ErroEstoque()
        quantidades[item.produto_id] = quantidades.get(item.produto_id, 0) + item.quantidade
    return quantidades


@transaction.atomic
def reservar_itens(usuario, itens):
    Usuario.objects.select_for_update().get(pk=usuario.pk)
    liberar_expiradas()
    quantidades = _quantidades(itens)
    produtos = list(Produto.objects.select_for_update().filter(pk__in=quantidades).order_by("pk"))
    if len(produtos) != len(quantidades):
        raise ErroEstoque()
    for produto in produtos:
        if (not produto.ativo or not produto.categoria.ativa or quantidades[produto.pk] > 10
                or quantidades[produto.pk] > estoque_disponivel(produto, ignorar_usuario=usuario)):
            raise ErroEstoque()

    expira_em = timezone.now() + timedelta(minutes=10)
    ReservaEstoque.objects.filter(usuario=usuario).exclude(produto_id__in=quantidades).update(ativa=False)
    for produto in produtos:
        ReservaEstoque.objects.update_or_create(
            usuario=usuario, produto=produto,
            defaults={"quantidade": quantidades[produto.pk], "expira_em": expira_em, "ativa": True},
        )
    return expira_em


def garantir_reservas(usuario, itens):
    liberar_expiradas()
    quantidades = _quantidades(itens)
    reservas = list(ReservaEstoque.objects.filter(usuario=usuario, ativa=True, expira_em__gt=timezone.now()))
    atuais = {reserva.produto_id: reserva.quantidade for reserva in reservas}
    if atuais != quantidades or not reservas:
        return reservar_itens(usuario, itens)
    for item in itens:
        if (not item.produto.ativo or not item.produto.categoria.ativa
                or item.quantidade > estoque_disponivel(item.produto, ignorar_usuario=usuario)):
            raise ErroEstoque()
    return min(reserva.expira_em for reserva in reservas)


@transaction.atomic
def dar_baixa(pedido):
    atual = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if atual.estoque_baixado:
        pedido.estoque_baixado = True
        return
    quantidades = _quantidades(atual.itens.all())
    produtos = list(Produto.objects.select_for_update().filter(pk__in=quantidades).order_by("pk"))
    for produto in produtos:
        if quantidades[produto.pk] > estoque_disponivel(produto, ignorar_usuario=atual.usuario):
            raise ErroEstoque()
    for produto in produtos:
        produto.estoque -= quantidades[produto.pk]
        produto.total_vendas += quantidades[produto.pk]
        produto.save(update_fields=["estoque", "total_vendas", "atualizado_em"])
    ReservaEstoque.objects.filter(usuario=atual.usuario, produto_id__in=quantidades).update(ativa=False)
    atual.estoque_baixado = True
    atual.save(update_fields=["estoque_baixado", "atualizado_em"])
    pedido.estoque_baixado = True


@transaction.atomic
def repor_estoque(pedido):
    atual = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if not atual.estoque_baixado:
        pedido.estoque_baixado = False
        return
    quantidades = _quantidades(atual.itens.all())
    produtos = Produto.objects.select_for_update().filter(pk__in=quantidades).order_by("pk")
    for produto in produtos:
        produto.estoque += quantidades[produto.pk]
        produto.total_vendas = max(0, produto.total_vendas - quantidades[produto.pk])
        produto.save(update_fields=["estoque", "total_vendas", "atualizado_em"])
    atual.estoque_baixado = False
    atual.save(update_fields=["estoque_baixado", "atualizado_em"])
    pedido.estoque_baixado = False
