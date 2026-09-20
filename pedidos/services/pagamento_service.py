import hashlib
import re
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone


class ErroPagamento(Exception):
    def __init__(self, erros):
        self.erros = erros
        super().__init__("Confira os dados de pagamento.")


class PagamentoRecusado(Exception):
    def __init__(self):
        super().__init__("Pagamento não autorizado. Tente outro cartão ou escolha PIX.")


def validar_luhn(numero):
    numero = re.sub(r"[ -]", "", str(numero))
    if not re.fullmatch(r"[0-9]{13,19}", numero) or len(set(numero)) == 1:
        return False
    soma = 0
    for indice, caractere in enumerate(reversed(numero)):
        digito = int(caractere)
        if indice % 2:
            digito *= 2
            if digito > 9:
                digito -= 9
        soma += digito
    return soma % 10 == 0


def validar_cartao(dados):
    erros = {}
    numero = re.sub(r"[ -]", "", str(dados.get("numero", "")))
    if not validar_luhn(numero):
        erros["numero"] = "Informe um número de cartão válido."
    validade = re.fullmatch(r"(0[1-9]|1[0-2])/([0-9]{2})", str(dados.get("validade", "")))
    hoje = timezone.localdate()
    if not validade or (2000 + int(validade[2]), int(validade[1])) <= (hoje.year, hoje.month):
        erros["validade"] = "Informe uma validade futura no formato MM/AA."
    if not re.fullmatch(r"[0-9]{3}", str(dados.get("cvv", ""))):
        erros["cvv"] = "Informe os 3 dígitos do CVV."
    if not str(dados.get("nome") or "").strip():
        erros["nome"] = "Informe o nome impresso no cartão."
    if erros:
        raise ErroPagamento(erros)
    return numero


def calcular_parcelas(principal, quantidade):
    try:
        quantidade = int(str(quantidade))
    except (ValueError, TypeError):
        raise ErroPagamento({"parcelas": "Escolha entre 1 e 12 parcelas."})
    if not 1 <= quantidade <= 12:
        raise ErroPagamento({"parcelas": "Escolha entre 1 e 12 parcelas."})
    total = Decimal(str(principal))
    # Os juros compostos incidem por todos os meses do parcelamento.
    if quantidade >= 4:
        total *= Decimal("1.025") ** quantidade
    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    parcela = (total / quantidade).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"parcelas": quantidade, "valor_parcela": parcela, "total": total}


def opcoes_parcelamento(principal):
    return [calcular_parcelas(principal, quantidade) for quantidade in range(1, 13)]


def processar_cartao(dados, total):
    numero = validar_cartao(dados)
    parcelas = calcular_parcelas(total, dados.get("parcelas", "1"))
    if numero == "4000000000000002":
        raise PagamentoRecusado()
    bandeira = "Visa" if numero.startswith("4") else "Outra"
    if numero[:2] in ("51", "52", "53", "54", "55"):
        bandeira = "Mastercard"
    return {
        "ultimos_digitos": numero[-4:], "bandeira": bandeira,
        "parcelas": parcelas["parcelas"], "valor_parcela": str(parcelas["valor_parcela"]),
        "total": str(parcelas["total"]),
    }


def gerar_pix(numero, total):
    codigo = f"DEMONSTRACAO-SEM-VALOR-PIX-{numero}-{total:.2f}"
    return {"codigo": codigo, "expira_em": timezone.now() + timedelta(minutes=30)}


def desenhar_qr(codigo):
    dados = hashlib.shake_256(codigo.encode("utf-8")).digest(441)
    quadrados = []
    for linha in range(21):
        for coluna in range(21):
            preenchido = dados[linha * 21 + coluna] % 2 == 0
            for inicio_x, inicio_y in ((0, 0), (14, 0), (0, 14)):
                x, y = coluna - inicio_x, linha - inicio_y
                if 0 <= x < 7 and 0 <= y < 7:
                    preenchido = x in (0, 6) or y in (0, 6) or (2 <= x <= 4 and 2 <= y <= 4)
            if preenchido:
                quadrados.append(f'<rect x="{coluna + 4}" y="{linha + 4}" width="1" height="1"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 29 29" role="img" '
            'aria-label="QR fictício, sem valor de pagamento" shape-rendering="crispEdges">'
            '<rect width="29" height="29" fill="white"/><g fill="black">'
            + "".join(quadrados) + "</g></svg>")
