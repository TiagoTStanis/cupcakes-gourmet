from decimal import Decimal

from django.utils import timezone

from pedidos.models import Cupom, CupomUso


class ErroCupom(Exception):
    pass


def validar_cupom(codigo, usuario, subtotal):
    if not codigo:
        raise ErroCupom("Informe o código do cupom.")

    codigo_limpo = str(codigo).strip()

    try:
        cupom = Cupom.objects.get(codigo__iexact=codigo_limpo)
    except Cupom.DoesNotExist:
        raise ErroCupom("Este cupom não está mais disponível.")

    if not cupom.ativo:
        raise ErroCupom("Este cupom não está mais disponível.")

    if cupom.data_validade < timezone.now():
        raise ErroCupom("Este cupom não está mais disponível.")

    if usuario and usuario.is_authenticated:
        if CupomUso.objects.filter(cupom=cupom, usuario=usuario).exists():
            raise ErroCupom("Você já usou este cupom em um pedido anterior.")

    subtotal = Decimal(str(subtotal))
    if subtotal < cupom.valor_minimo_pedido:
        valor_min_fmt = f"{cupom.valor_minimo_pedido:.2f}".replace(".", ",")
        raise ErroCupom(f"Este cupom é válido para compras acima de R$ {valor_min_fmt}.")

    return cupom


def calcular_desconto(cupom, subtotal):
    subtotal = Decimal(str(subtotal))
    if subtotal <= Decimal("0.00") or not cupom:
        return Decimal("0.00")

    if cupom.tipo == "PERCENTUAL":
        desconto = (subtotal * cupom.valor) / Decimal("100")
    elif cupom.tipo == "FIXO":
        desconto = cupom.valor
    else:
        desconto = Decimal("0.00")

    # O abatimento nunca pode ser superior ao valor dos produtos
    if desconto > subtotal:
        desconto = subtotal
    if desconto < Decimal("0.00"):
        desconto = Decimal("0.00")

    return desconto.quantize(Decimal("0.01"))


def registrar_uso(cupom, usuario):
    if not usuario or not usuario.is_authenticated:
        raise ErroCupom("Usuário deve estar autenticado para registrar uso do cupom.")
    return CupomUso.objects.create(cupom=cupom, usuario=usuario)
