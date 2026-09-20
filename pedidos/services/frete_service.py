from decimal import Decimal
import re

import requests

from pedidos.models import TabelaFreteUF


class ErroFrete(Exception):
    pass


def normalizar_cep(cep):
    if not cep:
        raise ErroFrete("CEP inválido. Por favor, verifique e tente novamente.")

    # Remove qualquer caractere que não seja dígito numérico
    cep_limpo = re.sub(r"\D", "", str(cep))

    if len(cep_limpo) != 8:
        raise ErroFrete("CEP inválido. Por favor, verifique e tente novamente.")

    return cep_limpo


def consultar_cep(cep):
    cep_limpo = normalizar_cep(cep)
    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"

    try:
        resposta = requests.get(url, timeout=3)
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError):
        raise ErroFrete("Não foi possível consultar o CEP no momento. Tente novamente.")

    if dados.get("erro") in (True, "true"):
        raise ErroFrete("CEP inválido. Por favor, verifique e tente novamente.")

    return {
        "cep": dados.get("cep", f"{cep_limpo[:5]}-{cep_limpo[5:]}"),
        "logradouro": dados.get("logradouro", ""),
        "bairro": dados.get("bairro", ""),
        "cidade": dados.get("localidade", ""),
        "localidade": dados.get("localidade", ""),
        "uf": dados.get("uf", "").upper(),
        "complemento": dados.get("complemento", ""),
    }


def calcular_frete(uf, subtotal_apos_desconto=Decimal("0.00")):
    if not uf:
        raise ErroFrete("Infelizmente não entregamos neste endereço ainda.")

    uf_normalizada = str(uf).strip().upper()

    try:
        tabela = TabelaFreteUF.objects.get(uf=uf_normalizada)
    except TabelaFreteUF.DoesNotExist:
        raise ErroFrete("Infelizmente não entregamos neste endereço ainda.")

    subtotal_apos_desconto = Decimal(str(subtotal_apos_desconto))

    # Frete grátis apenas se o subtotal após cupom for estritamente maior que 150,00
    if subtotal_apos_desconto > Decimal("150.00"):
        return {
            "uf": uf_normalizada,
            "valor": Decimal("0.00"),
            "prazo_dias": tabela.prazo_dias,
            "gratis": True,
            "valor_original": tabela.valor,
        }

    return {
        "uf": uf_normalizada,
        "valor": tabela.valor,
        "prazo_dias": tabela.prazo_dias,
        "gratis": False,
        "valor_original": tabela.valor,
    }


def consultar_e_calcular(cep, subtotal_apos_desconto=Decimal("0.00")):
    endereco = consultar_cep(cep)
    frete = calcular_frete(endereco["uf"], subtotal_apos_desconto=subtotal_apos_desconto)
    return {
        "endereco": endereco,
        "frete": frete,
    }
