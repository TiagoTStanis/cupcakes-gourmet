from decimal import Decimal

from pedidos.models import TabelaFreteUF

FRETE_PADRAO = {
    "PR": (Decimal("8.00"), 2),
    "SC": (Decimal("12.00"), 3),
    "RS": (Decimal("15.00"), 4),
    "SP": (Decimal("14.00"), 3),
    "RJ": (Decimal("18.00"), 4),
    "MG": (Decimal("18.00"), 4),
}


def carregar_tabela_frete():
    for uf, (valor, prazo) in FRETE_PADRAO.items():
        TabelaFreteUF.objects.update_or_create(
            uf=uf,
            defaults={
                "valor": valor,
                "prazo_dias": prazo,
            },
        )
