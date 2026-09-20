from carrinho.services.carrinho_service import obter_carrinho


def carrinho_contexto(request):
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {
            "carrinho_total_itens": 0,
            "total_itens_carrinho": 0,
        }

    try:
        carrinho = obter_carrinho(request.user)
        total = carrinho.total_itens
    except Exception:
        total = 0

    return {
        "carrinho_total_itens": total,
        "total_itens_carrinho": total,
    }
