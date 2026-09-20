from pedidos.services import frete_service, resumo_service
from usuarios.models import Endereco


def obter_endereco(usuario, endereco_id):
    try:
        return Endereco.objects.filter(usuario=usuario, pk=int(endereco_id)).first()
    except (ValueError, TypeError):
        return None


def selecionar_endereco(usuario, endereco, sessao):
    frete_service.calcular_frete(endereco.uf)
    sessao["checkout_endereco_id"] = endereco.pk
    sessao["frete_cep"] = endereco.cep
    sessao["frete_uf"] = endereco.uf


def resumo_checkout(usuario, carrinho, endereco, sessao):
    frete_service.calcular_frete(endereco.uf)
    return resumo_service.obter_resumo_carrinho(
        usuario, carrinho=carrinho, sessao=sessao, cep=endereco.cep, uf=endereco.uf,
    )
