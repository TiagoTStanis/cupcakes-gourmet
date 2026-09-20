import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from carrinho.services import carrinho_service
from pedidos.services import cupom_service, frete_service, historico_service, resumo_service
from pedidos.services.cupom_service import ErroCupom
from pedidos.services.frete_service import ErroFrete
from pedidos.models import Notificacao, Pedido
from pedidos.services import checkout_service, estoque_service
from pedidos.services import pagamento_service, pedido_service
from pedidos.services.estoque_service import ErroEstoque
from usuarios.forms import EnderecoForm


def _extrair_dados(request):
    if request.content_type == "application/json" and request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST


def _verificar_autenticacao(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"sucesso": False, "erro": "Entre na sua conta para continuar."},
            status=401,
        )
    return None


@require_POST
def consultar_cep(request):
    erro_auth = _verificar_autenticacao(request)
    if erro_auth:
        return erro_auth

    dados = _extrair_dados(request)
    cep = dados.get("cep")

    if not cep:
        return JsonResponse(
            {"sucesso": False, "erro": "CEP inválido. Por favor, verifique e tente novamente."},
            status=400,
        )

    try:
        endereco = frete_service.consultar_cep(cep)
        carrinho = carrinho_service.obter_carrinho(request.user)

        resumo_atual = resumo_service.obter_resumo_carrinho(
            request.user,
            carrinho=carrinho,
            sessao=request.session,
        )
        subtotal_com_desconto = resumo_atual["subtotal_com_desconto"]

        frete = frete_service.calcular_frete(endereco["uf"], subtotal_apos_desconto=subtotal_com_desconto)

        # Guarda dados do frete na sessão do usuário
        request.session["frete_cep"] = endereco["cep"]
        request.session["frete_uf"] = endereco["uf"]
        request.session["frete_logradouro"] = endereco.get("logradouro", "")
        request.session["frete_bairro"] = endereco.get("bairro", "")
        request.session["frete_cidade"] = endereco.get("cidade", "")
        request.session["frete_valor"] = str(frete["valor"])
        request.session["frete_prazo"] = frete["prazo_dias"]
        request.session["frete_gratis"] = frete["gratis"]
        request.session.modified = True

        resumo = resumo_service.obter_resumo_carrinho(
            request.user,
            carrinho=carrinho,
            sessao=request.session,
        )

        return JsonResponse({
            "sucesso": True,
            "endereco": endereco,
            "frete": {
                "valor": f"{frete['valor']:.2f}",
                "valor_formatado": "Grátis" if frete["gratis"] else f"R$ {frete['valor']:.2f}".replace(".", ","),
                "prazo_dias": frete["prazo_dias"],
                "gratis": frete["gratis"],
                "uf": frete["uf"],
            },
            "resumo": {
                "subtotal": f"{resumo['subtotal']:.2f}",
                "subtotal_formatado": resumo["subtotal_formatado"],
                "desconto": f"{resumo['desconto']:.2f}",
                "desconto_formatado": resumo["desconto_formatado"],
                "frete": f"{resumo['frete']:.2f}",
                "frete_formatado": resumo["frete_formatado"],
                "frete_gratis": resumo["frete_gratis"],
                "total": f"{resumo['total']:.2f}",
                "total_formatado": resumo["total_formatado"],
                "prazo_dias": resumo["prazo_dias"],
                "cupom_codigo": resumo["cupom_codigo"],
                "cep": resumo["cep"],
                "uf": resumo["uf"],
            },
        })
    except ErroFrete as erro:
        return JsonResponse({"sucesso": False, "erro": str(erro)}, status=400)


@require_POST
def aplicar_cupom(request):
    erro_auth = _verificar_autenticacao(request)
    if erro_auth:
        return erro_auth

    dados = _extrair_dados(request)
    codigo = dados.get("codigo") or dados.get("cupom")

    if not codigo:
        return JsonResponse(
            {"sucesso": False, "erro": "Informe o código do cupom."},
            status=400,
        )

    try:
        carrinho = carrinho_service.obter_carrinho(request.user)
        totais = carrinho_service.calcular_totais(carrinho)
        subtotal = totais["total_geral"]

        cupom = cupom_service.validar_cupom(codigo, request.user, subtotal)
        request.session["cupom_codigo"] = cupom.codigo
        request.session.modified = True

        resumo = resumo_service.obter_resumo_carrinho(
            request.user,
            carrinho=carrinho,
            sessao=request.session,
        )

        return JsonResponse({
            "sucesso": True,
            "mensagem": f"Cupom {cupom.codigo} aplicado com sucesso.",
            "cupom": {
                "codigo": cupom.codigo,
                "tipo": cupom.tipo,
                "valor": f"{cupom.valor:.2f}",
                "desconto": f"{resumo['desconto']:.2f}",
                "desconto_formatado": resumo["desconto_formatado"],
            },
            "resumo": {
                "subtotal": f"{resumo['subtotal']:.2f}",
                "subtotal_formatado": resumo["subtotal_formatado"],
                "desconto": f"{resumo['desconto']:.2f}",
                "desconto_formatado": resumo["desconto_formatado"],
                "frete": f"{resumo['frete']:.2f}",
                "frete_formatado": resumo["frete_formatado"],
                "frete_gratis": resumo["frete_gratis"],
                "total": f"{resumo['total']:.2f}",
                "total_formatado": resumo["total_formatado"],
                "prazo_dias": resumo["prazo_dias"],
                "cupom_codigo": resumo["cupom_codigo"],
                "cep": resumo["cep"],
                "uf": resumo["uf"],
            },
        })
    except ErroCupom as erro:
        return JsonResponse({"sucesso": False, "erro": str(erro)}, status=400)


@require_POST
def remover_cupom(request):
    erro_auth = _verificar_autenticacao(request)
    if erro_auth:
        return erro_auth

    if "cupom_codigo" in request.session:
        del request.session["cupom_codigo"]
        request.session.modified = True

    resumo = resumo_service.obter_resumo_carrinho(request.user, sessao=request.session)

    return JsonResponse({
        "sucesso": True,
        "mensagem": "Cupom removido.",
        "resumo": {
            "subtotal": f"{resumo['subtotal']:.2f}",
            "subtotal_formatado": resumo["subtotal_formatado"],
            "desconto": f"{resumo['desconto']:.2f}",
            "desconto_formatado": resumo["desconto_formatado"],
            "frete": f"{resumo['frete']:.2f}",
            "frete_formatado": resumo["frete_formatado"],
            "frete_gratis": resumo["frete_gratis"],
            "total": f"{resumo['total']:.2f}",
            "total_formatado": resumo["total_formatado"],
            "prazo_dias": resumo["prazo_dias"],
            "cupom_codigo": None,
            "cep": resumo["cep"],
            "uf": resumo["uf"],
        },
    })


@require_GET
def obter_resumo(request):
    erro_auth = _verificar_autenticacao(request)
    if erro_auth:
        return erro_auth

    resumo = resumo_service.obter_resumo_carrinho(request.user, sessao=request.session)

    return JsonResponse({
        "sucesso": True,
        "resumo": {
            "subtotal": f"{resumo['subtotal']:.2f}",
            "subtotal_formatado": resumo["subtotal_formatado"],
            "desconto": f"{resumo['desconto']:.2f}",
            "desconto_formatado": resumo["desconto_formatado"],
            "frete": f"{resumo['frete']:.2f}",
            "frete_formatado": resumo["frete_formatado"],
            "frete_gratis": resumo["frete_gratis"],
            "total": f"{resumo['total']:.2f}",
            "total_formatado": resumo["total_formatado"],
            "prazo_dias": resumo["prazo_dias"],
            "cupom_codigo": resumo["cupom_codigo"],
            "quantidade_total": resumo["quantidade_total"],
            "cep": resumo["cep"],
            "uf": resumo["uf"],
        },
    })


def _preparar_checkout(request, renovar=False):
    carrinho = carrinho_service.obter_carrinho(request.user)
    itens = list(carrinho.itens.select_related("produto", "produto__categoria"))
    estoque_service.liberar_expiradas()
    if not itens:
        estoque_service.liberar_do_usuario(request.user)
        messages.warning(request, "Seu carrinho está vazio. Adicione um cupcake para continuar.")
        return None
    try:
        if renovar:
            expira_em = estoque_service.reservar_itens(request.user, itens)
        else:
            expira_em = estoque_service.garantir_reservas(request.user, itens)
    except ErroEstoque as erro:
        estoque_service.liberar_do_usuario(request.user)
        messages.warning(request, str(erro))
        return None
    return {"carrinho": carrinho, "itens": itens, "expira_em": expira_em}


def _endereco_checkout(request):
    endereco = checkout_service.obter_endereco(request.user, request.session.get("checkout_endereco_id"))
    if endereco:
        try:
            frete_service.calcular_frete(endereco.uf)
            return endereco
        except ErroFrete as erro:
            messages.warning(request, str(erro))
    request.session.pop("checkout_endereco_id", None)
    return None


@login_required
@require_http_methods(["GET", "POST"])
def checkout_endereco(request):
    pendente = pedido_service.obter_pix_pendente(request.user)
    if pendente:
        return redirect("pedidos:pedido_detalhe", numero=pendente.numero)
    contexto = _preparar_checkout(request, renovar=request.method == "GET")
    if contexto is None:
        return redirect("carrinho:detalhe")
    formulario = EnderecoForm()
    selecionado = str(request.session.get("checkout_endereco_id", ""))
    novo_endereco = False
    if request.method == "POST":
        selecionado = request.POST.get("endereco_id", "")
        novo_endereco = selecionado == "novo"
        endereco = None
        if novo_endereco:
            formulario = EnderecoForm(request.POST)
            if formulario.is_valid():
                endereco = formulario.save(commit=False)
                endereco.usuario = request.user
        else:
            endereco = checkout_service.obter_endereco(request.user, selecionado)
            if endereco is None:
                messages.error(request, "Selecione um dos seus endereços.")
        if endereco:
            try:
                frete_service.calcular_frete(endereco.uf)
                if novo_endereco:
                    endereco.save()
                checkout_service.selecionar_endereco(request.user, endereco, request.session)
                return redirect("pedidos:checkout_pagamento")
            except ErroFrete as erro:
                messages.error(request, str(erro))
    contexto.update({
        "etapa": 1, "formulario": formulario,
        "enderecos": request.user.enderecos.order_by("-principal", "pk"),
        "selecionado": selecionado, "novo_endereco": novo_endereco,
    })
    return render(request, "pedidos/endereco.html", contexto)


@login_required
@require_http_methods(["GET", "POST"])
def checkout_pagamento(request):
    pendente = pedido_service.obter_pix_pendente(request.user)
    if pendente:
        return redirect("pedidos:pedido_detalhe", numero=pendente.numero)
    contexto = _preparar_checkout(request)
    if contexto is None:
        return redirect("carrinho:detalhe")
    endereco = _endereco_checkout(request)
    if endereco is None:
        return redirect("pedidos:checkout_endereco")
    if request.method == "POST":
        forma = request.POST.get("forma_pagamento")
        if forma in dict(Pedido.FORMA_PAGAMENTO_CHOICES):
            request.session["checkout_forma_pagamento"] = forma
            return redirect("pedidos:checkout_resumo")
        messages.error(request, "Escolha cartão ou PIX para continuar.")
    contexto.update({
        "etapa": 2, "formas": Pedido.FORMA_PAGAMENTO_CHOICES,
        "forma_selecionada": request.session.get("checkout_forma_pagamento"),
        "resumo": checkout_service.resumo_checkout(request.user, contexto["carrinho"], endereco, request.session),
        "endereco": endereco,
    })
    contexto["parcelas"] = pagamento_service.opcoes_parcelamento(contexto["resumo"]["total"])
    return render(request, "pedidos/pagamento.html", contexto)


def _resumo_checkout(request):
    contexto = _preparar_checkout(request)
    if contexto is None:
        return None, redirect("carrinho:detalhe")
    endereco = _endereco_checkout(request)
    if endereco is None:
        return None, redirect("pedidos:checkout_endereco")
    forma = request.session.get("checkout_forma_pagamento")
    if forma not in dict(Pedido.FORMA_PAGAMENTO_CHOICES):
        return None, redirect("pedidos:checkout_pagamento")
    contexto.update({
        "etapa": 3, "endereco": endereco,
        "forma_pagamento": dict(Pedido.FORMA_PAGAMENTO_CHOICES)[forma],
        "resumo": checkout_service.resumo_checkout(request.user, contexto["carrinho"], endereco, request.session),
    })
    return contexto, None


@login_required
@require_GET
def checkout_resumo(request):
    pendente = pedido_service.obter_pix_pendente(request.user)
    if pendente:
        return redirect("pedidos:pedido_detalhe", numero=pendente.numero)
    contexto, redirecionamento = _resumo_checkout(request)
    if redirecionamento is not None:
        return redirecionamento
    contexto["cartao"] = request.session.get("checkout_forma_pagamento") == "CARTAO"
    contexto["parcelas"] = pagamento_service.opcoes_parcelamento(contexto["resumo"]["total"])
    return render(request, "pedidos/resumo.html", contexto)


@login_required
@sensitive_post_parameters("numero", "cvv", "validade", "nome")
@require_POST
def checkout_confirmar(request):
    pendente = pedido_service.obter_pix_pendente(request.user)
    if pendente:
        return redirect("pedidos:pedido_detalhe", numero=pendente.numero)
    forma = request.POST.get("forma_pagamento")
    if forma in dict(Pedido.FORMA_PAGAMENTO_CHOICES):
        request.session["checkout_forma_pagamento"] = forma
    contexto, redirecionamento = _resumo_checkout(request)
    if redirecionamento is not None:
        return redirecionamento
    try:
        pedido = pedido_service.criar_pedido(
            request.user, contexto["carrinho"], contexto["endereco"], request.session,
            request.session["checkout_forma_pagamento"], request.POST,
        )
    except pagamento_service.ErroPagamento as erro:
        contexto.update({
            "etapa": 2, "erros": erro.erros, "formas": Pedido.FORMA_PAGAMENTO_CHOICES,
            "forma_selecionada": request.session["checkout_forma_pagamento"],
            "parcelas": pagamento_service.opcoes_parcelamento(contexto["resumo"]["total"]),
        })
        return render(request, "pedidos/pagamento.html", contexto)
    except pagamento_service.PagamentoRecusado as erro:
        estoque_service.liberar_do_usuario(request.user)
        return render(request, "pedidos/recusado.html", {"mensagem": str(erro)})
    except ErroEstoque as erro:
        messages.warning(request, str(erro))
        return redirect("carrinho:detalhe")
    return redirect("pedidos:pedido_detalhe", numero=pedido.numero)


@login_required
@require_GET
def pedido_detalhe(request, numero):
    pedido = get_object_or_404(Pedido, numero=numero, usuario=request.user)
    pedido = pedido_service.verificar_expiracao(pedido, request.user)
    if pedido.status == "AGUARDANDO_PAGAMENTO" and pedido.forma_pagamento == "PIX":
        return render(request, "pedidos/pix.html", {
            "pedido": pedido, **pedido_service.obter_rastreamento(pedido), "qr": pagamento_service.desenhar_qr(pedido.detalhes_pagamento["codigo"]),
        })
    return render(request, "pedidos/confirmacao.html", {"pedido": pedido, **pedido_service.obter_rastreamento(pedido)})


@login_required
@require_POST
def confirmar_pix(request, numero):
    pedido = get_object_or_404(Pedido, numero=numero, usuario=request.user)
    try:
        pedido_service.confirmar_pix(pedido, request.user)
    except ErroEstoque as erro:
        messages.warning(request, str(erro))
    return redirect("pedidos:pedido_detalhe", numero=pedido.numero)


@login_required
@require_GET
def notificacoes(request):
    avisos = Notificacao.objects.filter(usuario=request.user).select_related("pedido")
    return render(request, "pedidos/notificacoes.html", {"notificacoes": avisos})


@login_required
@require_POST
def marcar_notificacao_lida(request, pk):
    aviso = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    Notificacao.objects.filter(pk=aviso.pk, usuario=request.user).update(lida=True)
    return redirect("pedidos:notificacoes")


@login_required
@require_POST
def marcar_todas_lidas(request):
    Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
    return redirect("pedidos:notificacoes")


@login_required
@require_GET
def historico(request):
    pedido_service.cancelar_pix_vencidos()
    pedidos_qs = historico_service.listar_pedidos(request.user)
    paginador = Paginator(pedidos_qs, 10)
    numero_pagina = request.GET.get("pagina")
    pagina = paginador.get_page(numero_pagina)
    return render(request, "pedidos/historico.html", {
        "pagina": pagina,
        "pedidos": pagina.object_list,
    })


@login_required
@require_POST
def repetir_pedido(request, numero):
    pedido = get_object_or_404(Pedido, numero=numero, usuario=request.user)
    adicionados, erros = historico_service.repetir_pedido(request.user, pedido)
    if adicionados:
        messages.success(request, "Itens do pedido foram adicionados ao seu carrinho.")
    for erro in erros:
        messages.warning(request, erro)
    return redirect("carrinho:detalhe")

