import re
from datetime import timedelta
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from carrinho.models import Carrinho
from pedidos.models import CupomUso, HistoricoStatus, ItemPedido, Notificacao, Pedido, ReservaEstoque, TabelaFreteUF
from pedidos.services import checkout_service, cupom_service, estoque_service, pagamento_service
from usuarios.models import Usuario


class ErroPedido(Exception):
    pass


@transaction.atomic
def alterar_status(pedido, novo_status, motivo=""):
    Usuario.objects.select_for_update().get(pk=pedido.usuario_id)
    atual = Pedido.objects.select_for_update().get(pk=pedido.pk)
    transicoes = {
        "AGUARDANDO_PAGAMENTO": ["PAGAMENTO_CONFIRMADO", "CANCELADO"],
        "PAGAMENTO_CONFIRMADO": ["EM_PREPARACAO"],
        "EM_PREPARACAO": ["SAIU_PARA_ENTREGA", "CANCELADO"],
        "SAIU_PARA_ENTREGA": ["ENTREGUE"],
    }
    if novo_status not in transicoes.get(atual.status, []):
        destino = dict(Pedido.STATUS_CHOICES).get(novo_status, novo_status)
        raise ErroPedido(f"Não é permitido mudar de {atual.get_status_display()} para {destino}.")
    if novo_status == "PAGAMENTO_CONFIRMADO":
        if atual.forma_pagamento == "PIX" and atual.pix_expira_em and atual.pix_expira_em <= timezone.now():
            raise ErroPedido("PIX expirado. O pagamento não pode ser confirmado.")
        estoque_service.dar_baixa(atual)
    if novo_status == "CANCELADO":
        # O prazo identifica as reservas do pedido, preservando um novo carrinho.
        if atual.pix_expira_em:
            ReservaEstoque.objects.filter(
                usuario_id=atual.usuario_id, produto_id__in=atual.itens.values("produto_id"),
                expira_em=atual.pix_expira_em,
            ).update(ativa=False)
        if atual.status == "AGUARDANDO_PAGAMENTO" and atual.cupom_id:
            CupomUso.objects.filter(cupom_id=atual.cupom_id, usuario_id=atual.usuario_id).delete()
        if atual.estoque_baixado:
            estoque_service.repor_estoque(atual)
    atual.status = novo_status
    atual.save(update_fields=["status", "atualizado_em"])
    HistoricoStatus.objects.create(pedido=atual, status=novo_status)
    titulo = "Pedido cancelado" if novo_status == "CANCELADO" else atual.get_status_display()
    mensagem = f"Pedido {atual.numero}: {titulo}."
    if novo_status == "CANCELADO" and motivo:
        mensagem = f"Pedido {atual.numero}: {titulo}: {motivo}."
    Notificacao.objects.create(usuario_id=atual.usuario_id, pedido=atual, titulo=titulo, mensagem=mensagem)
    pedido.status = atual.status
    pedido.estoque_baixado = atual.estoque_baixado
    return atual


@transaction.atomic
def verificar_expiracao(pedido, usuario):
    Usuario.objects.select_for_update().get(pk=usuario.pk)
    atual = Pedido.objects.select_for_update().get(pk=pedido.pk, usuario=usuario)
    if (atual.forma_pagamento == "PIX" and atual.status == "AGUARDANDO_PAGAMENTO"
            and atual.pix_expira_em and atual.pix_expira_em <= timezone.now()):
        atual = alterar_status(atual, "CANCELADO", motivo="PIX expirado")
    return atual


def cancelar_pix_vencidos():
    vencidos = Pedido.objects.select_related("usuario").filter(
        forma_pagamento="PIX", status="AGUARDANDO_PAGAMENTO", pix_expira_em__lte=timezone.now()
    )
    for pedido in vencidos:
        verificar_expiracao(pedido, pedido.usuario)


def obter_rastreamento(pedido):
    horarios = {registro.status: registro.criado_em for registro in pedido.historico_status.all()}
    etapas = []
    for status, nome in Pedido.STATUS_CHOICES[1:5]:
        etapas.append({
            "nome": nome, "horario": horarios.get(status), "atual": pedido.status == status,
        })
    previsao = None
    uf = re.search(r"/([A-Z]{2})(?:\s|$)", pedido.endereco_entrega)
    if uf and pedido.status != "CANCELADO":
        frete = TabelaFreteUF.objects.filter(uf=uf.group(1)).first()
        if frete:
            inicio = horarios.get("PAGAMENTO_CONFIRMADO", pedido.criado_em)
            previsao = timezone.localdate(inicio) + timedelta(days=frete.prazo_dias)
    cancelamento = None
    if pedido.status == "CANCELADO":
        cancelamento = Notificacao.objects.filter(pedido=pedido, titulo="Pedido cancelado").first()
    return {"etapas": etapas, "previsao_entrega": previsao, "cancelamento": cancelamento}


def obter_pix_pendente(usuario):
    for pedido in Pedido.objects.filter(usuario=usuario, forma_pagamento="PIX", status="AGUARDANDO_PAGAMENTO"):
        pedido = verificar_expiracao(pedido, usuario)
        if pedido.status == "AGUARDANDO_PAGAMENTO":
            return pedido
    return None


@transaction.atomic
def criar_pedido(usuario, carrinho, endereco, sessao, forma, dados=None):
    Usuario.objects.select_for_update().get(pk=usuario.pk)
    carrinho = Carrinho.objects.select_for_update().get(pk=carrinho.pk, usuario=usuario)
    if endereco.usuario_id != usuario.pk:
        raise PermissionDenied
    pendente = obter_pix_pendente(usuario)
    if pendente:
        return pendente
    itens = list(carrinho.itens.select_related("produto", "produto__categoria"))
    if not itens:
        raise estoque_service.ErroEstoque()
    estoque_service.garantir_reservas(usuario, itens)
    resumo = checkout_service.resumo_checkout(usuario, carrinho, endereco, sessao)
    if forma == "CARTAO":
        detalhes = pagamento_service.processar_cartao(dados or {}, resumo["total"])
    elif forma == "PIX":
        detalhes = {}
    else:
        raise pagamento_service.ErroPagamento({"forma_pagamento": "Escolha cartão ou PIX."})
    numero = f"CG-{timezone.localdate():%y%m%d}-{uuid4().hex[:10].upper()}"
    expira_em = None
    if forma == "PIX":
        pix = pagamento_service.gerar_pix(numero, resumo["total"])
        expira_em = pix["expira_em"]
        detalhes = {"codigo": pix["codigo"]}
    pedido = Pedido.objects.create(
        numero=numero, usuario=usuario,
        endereco_entrega=(f"{endereco.logradouro}, {endereco.numero} {endereco.complemento}\n"
                          f"{endereco.bairro} — {endereco.cidade}/{endereco.uf}\nCEP {endereco.cep}"),
        subtotal=resumo["subtotal"], valor_desconto=resumo["desconto"], cupom=resumo["cupom"],
        valor_frete=resumo["frete"], valor_total=resumo["total"], forma_pagamento=forma,
        detalhes_pagamento=detalhes, pix_expira_em=expira_em,
    )
    for item in itens:
        ItemPedido.objects.create(
            pedido=pedido, produto=item.produto, nome_produto=item.produto.nome,
            preco_unitario=item.produto.preco, quantidade=item.quantidade, subtotal=item.subtotal,
        )
    if pedido.cupom:
        cupom_service.registrar_uso(pedido.cupom, usuario)
    if forma == "CARTAO":
        alterar_status(pedido, "PAGAMENTO_CONFIRMADO")
    else:
        ReservaEstoque.objects.filter(usuario=usuario, ativa=True).update(expira_em=expira_em)
        HistoricoStatus.objects.create(pedido=pedido, status=pedido.status)
    # A limpeza normal do carrinho também liberaria as reservas do PIX.
    carrinho.itens.all().delete()
    carrinho.save()
    for chave in list(sessao.keys()):
        if chave == "cupom_codigo" or chave.startswith(("frete_", "checkout_")):
            sessao.pop(chave, None)
    return pedido


@transaction.atomic
def confirmar_pix(pedido, usuario):
    Usuario.objects.select_for_update().get(pk=usuario.pk)
    atual = verificar_expiracao(pedido, usuario)
    if atual.forma_pagamento != "PIX" or atual.status != "AGUARDANDO_PAGAMENTO":
        return atual
    return alterar_status(atual, "PAGAMENTO_CONFIRMADO")
