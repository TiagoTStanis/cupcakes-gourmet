from decimal import Decimal

from carrinho.services import carrinho_service
from pedidos.services import cupom_service, frete_service
from pedidos.services.cupom_service import ErroCupom
from pedidos.services.frete_service import ErroFrete


def obter_resumo_carrinho(usuario, carrinho=None, sessao=None, cupom_codigo=None, cep=None, uf=None):
    if carrinho is None:
        carrinho = carrinho_service.obter_carrinho(usuario)

    totais = carrinho_service.calcular_totais(carrinho)
    subtotal = totais["total_geral"]

    if sessao is not None:
        if cupom_codigo is None:
            cupom_codigo = sessao.get("cupom_codigo")
        if cep is None:
            cep = sessao.get("frete_cep")
        if uf is None:
            uf = sessao.get("frete_uf")

    cupom = None
    desconto = Decimal("0.00")

    if cupom_codigo:
        try:
            cupom = cupom_service.validar_cupom(cupom_codigo, usuario, subtotal)
            desconto = cupom_service.calcular_desconto(cupom, subtotal)
        except ErroCupom:
            cupom = None
            desconto = Decimal("0.00")
            if sessao is not None and "cupom_codigo" in sessao:
                sessao.pop("cupom_codigo", None)

    subtotal_com_desconto = max(Decimal("0.00"), subtotal - desconto)

    valor_frete = Decimal("0.00")
    prazo_dias = None
    frete_gratis = False

    if uf:
        try:
            frete_info = frete_service.calcular_frete(uf, subtotal_apos_desconto=subtotal_com_desconto)
            valor_frete = frete_info["valor"]
            prazo_dias = frete_info["prazo_dias"]
            frete_gratis = frete_info["gratis"]
        except ErroFrete:
            valor_frete = Decimal("0.00")
            prazo_dias = None
            frete_gratis = False
            if sessao is not None:
                sessao.pop("frete_cep", None)
                sessao.pop("frete_uf", None)
                sessao.pop("frete_valor", None)
                sessao.pop("frete_prazo", None)
                sessao.pop("frete_gratis", None)

    total = subtotal_com_desconto + valor_frete

    return {
        "subtotal": subtotal,
        "desconto": desconto,
        "subtotal_com_desconto": subtotal_com_desconto,
        "frete": valor_frete,
        "prazo_dias": prazo_dias,
        "gratis": frete_gratis,
        "frete_gratis": frete_gratis,
        "total": total,
        "cupom": cupom,
        "cupom_codigo": cupom.codigo if cupom else None,
        "cep": cep,
        "uf": uf,
        "quantidade_total": totais["quantidade_total"],
        "subtotal_formatado": f"R$ {subtotal:.2f}".replace(".", ","),
        "desconto_formatado": f"R$ {desconto:.2f}".replace(".", ","),
        "frete_formatado": "Grátis" if frete_gratis else (f"R$ {valor_frete:.2f}".replace(".", ",") if uf else "—"),
        "total_formatado": f"R$ {total:.2f}".replace(".", ","),
    }
