from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogo.models import Categoria, Produto
from catalogo.services.busca_service import normalizar_texto
from painel.decorators import staff_necessario
from painel.forms import CategoriaForm, ProdutoForm
from pedidos.models import Pedido
from pedidos.services import pedido_service
from pedidos.services.estoque_service import ErroEstoque
from pedidos.services.pedido_service import ErroPedido

PROXIMA_ETAPA = {
    "AGUARDANDO_PAGAMENTO": "PAGAMENTO_CONFIRMADO",
    "PAGAMENTO_CONFIRMADO": "EM_PREPARACAO",
    "EM_PREPARACAO": "SAIU_PARA_ENTREGA",
    "SAIU_PARA_ENTREGA": "ENTREGUE",
}


@staff_necessario
def inicio(request):
    pedido_service.cancelar_pix_vencidos()
    pedidos_status = [
        {
            "status": status,
            "nome": nome,
            "total": Pedido.objects.filter(status=status).count(),
        }
        for status, nome in Pedido.STATUS_CHOICES
    ]
    produtos_ativos_total = Produto.objects.filter(ativo=True).count()
    produtos_estoque_baixo_total = Produto.objects.filter(ativo=True, estoque__lte=5).count()
    total_pedidos = Pedido.objects.count()

    contexto = {
        "pedidos_status": pedidos_status,
        "produtos_ativos_total": produtos_ativos_total,
        "produtos_estoque_baixo_total": produtos_estoque_baixo_total,
        "total_pedidos": total_pedidos,
        "secao_painel": "inicio",
    }
    return render(request, "painel/inicio.html", contexto)


@staff_necessario
def produtos_lista(request):
    termo = request.GET.get("q", "").strip()
    categoria_slug = request.GET.get("categoria", "").strip()
    ativo_filtro = request.GET.get("ativo", "").strip()
    estoque_baixo = request.GET.get("estoque_baixo", "").strip()

    qs = Produto.objects.all().select_related("categoria").order_by("-criado_em", "-pk")
    if termo:
        termo_norm = normalizar_texto(termo)
        if termo_norm:
            qs = qs.filter(nome_busca__icontains=termo_norm)
    if categoria_slug:
        qs = qs.filter(categoria__slug=categoria_slug)
    if ativo_filtro == "1":
        qs = qs.filter(ativo=True)
    elif ativo_filtro == "0":
        qs = qs.filter(ativo=False)
    if estoque_baixo == "1":
        qs = qs.filter(estoque__lte=5)

    paginador = Paginator(qs, 10)
    pagina_num = request.GET.get("pagina")
    pagina = paginador.get_page(pagina_num)

    params = request.GET.copy()
    params.pop("pagina", None)
    querystring = f"&{params.urlencode()}" if params else ""

    contexto = {
        "pagina": pagina,
        "produtos": pagina.object_list,
        "categorias": Categoria.objects.all().order_by("nome"),
        "termo": termo,
        "categoria_slug": categoria_slug,
        "ativo_filtro": ativo_filtro,
        "estoque_baixo": estoque_baixo,
        "querystring": querystring,
        "secao_painel": "produtos",
    }
    return render(request, "painel/produtos_lista.html", contexto)


@staff_necessario
def produto_criar(request):
    if request.method == "POST":
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            produto = form.save()
            messages.success(request, f"Cupcake '{produto.nome}' criado com sucesso.")
            return redirect("painel:produtos_lista")
    else:
        form = ProdutoForm()

    contexto = {
        "form": form,
        "titulo": "Novo Cupcake",
        "secao_painel": "produtos",
    }
    return render(request, "painel/produto_form.html", contexto)


@staff_necessario
def produto_editar(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == "POST":
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            produto = form.save()
            messages.success(request, f"Cupcake '{produto.nome}' atualizado com sucesso.")
            return redirect("painel:produtos_lista")
    else:
        form = ProdutoForm(instance=produto)

    contexto = {
        "form": form,
        "produto": produto,
        "titulo": f"Editar {produto.nome}",
        "secao_painel": "produtos",
    }
    return render(request, "painel/produto_form.html", contexto)


@staff_necessario
@require_POST
def produto_desativar(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    produto.ativo = False
    produto.save(update_fields=["ativo", "atualizado_em"])
    messages.success(
        request,
        f"Cupcake '{produto.nome}' desativado com sucesso. Ele não aparecerá mais na vitrine, mas continua no histórico dos pedidos.",
    )
    return redirect("painel:produtos_lista")


@staff_necessario
@require_POST
def produto_reativar(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    produto.ativo = True
    produto.save(update_fields=["ativo", "atualizado_em"])
    messages.success(request, f"Cupcake '{produto.nome}' reativado com sucesso.")
    return redirect("painel:produtos_lista")


@staff_necessario
def categorias_lista(request):
    categorias = Categoria.objects.all().order_by("nome")
    contexto = {
        "categorias": categorias,
        "secao_painel": "categorias",
    }
    return render(request, "painel/categorias_lista.html", contexto)


@staff_necessario
def categoria_criar(request):
    if request.method == "POST":
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f"Categoria '{categoria.nome}' cadastrada com sucesso.")
            return redirect("painel:categorias_lista")
    else:
        form = CategoriaForm()

    contexto = {
        "form": form,
        "titulo": "Nova Categoria",
        "secao_painel": "categorias",
    }
    return render(request, "painel/categoria_form.html", contexto)


@staff_necessario
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == "POST":
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f"Categoria '{categoria.nome}' atualizada com sucesso.")
            return redirect("painel:categorias_lista")
    else:
        form = CategoriaForm(instance=categoria)

    contexto = {
        "form": form,
        "categoria": categoria,
        "titulo": f"Editar {categoria.nome}",
        "secao_painel": "categorias",
    }
    return render(request, "painel/categoria_form.html", contexto)


@staff_necessario
@require_POST
def categoria_desativar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    categoria.ativa = False
    categoria.save(update_fields=["ativa"])
    messages.success(request, f"Categoria '{categoria.nome}' desativada.")
    return redirect("painel:categorias_lista")


@staff_necessario
@require_POST
def categoria_reativar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    categoria.ativa = True
    categoria.save(update_fields=["ativa"])
    messages.success(request, f"Categoria '{categoria.nome}' reativada.")
    return redirect("painel:categorias_lista")


@staff_necessario
def pedidos_lista(request):
    pedido_service.cancelar_pix_vencidos()
    status_filtro = request.GET.get("status", "").strip()
    data_inicio = request.GET.get("data_inicio", "").strip()
    data_fim = request.GET.get("data_fim", "").strip()
    cliente_filtro = request.GET.get("cliente", "").strip()

    qs = Pedido.objects.select_related("usuario").all().order_by("-criado_em", "-pk")
    if status_filtro:
        qs = qs.filter(status=status_filtro)
    if data_inicio:
        qs = qs.filter(criado_em__date__gte=data_inicio)
    if data_fim:
        qs = qs.filter(criado_em__date__lte=data_fim)
    if cliente_filtro:
        qs = qs.filter(
            Q(usuario__nome_completo__icontains=cliente_filtro)
            | Q(usuario__email__icontains=cliente_filtro)
        )

    paginador = Paginator(qs, 10)
    pagina_num = request.GET.get("pagina")
    pagina = paginador.get_page(pagina_num)

    params = request.GET.copy()
    params.pop("pagina", None)
    querystring = f"&{params.urlencode()}" if params else ""

    contexto = {
        "pagina": pagina,
        "pedidos": pagina.object_list,
        "status_choices": Pedido.STATUS_CHOICES,
        "status_filtro": status_filtro,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "cliente_filtro": cliente_filtro,
        "querystring": querystring,
        "secao_painel": "pedidos",
    }
    return render(request, "painel/pedidos_lista.html", contexto)


@staff_necessario
def pedido_detalhe(request, numero):
    pedido_service.cancelar_pix_vencidos()
    pedido = get_object_or_404(
        Pedido.objects.select_related("usuario", "cupom").prefetch_related("itens__produto"),
        numero=numero,
    )
    proximo_status = PROXIMA_ETAPA.get(pedido.status)
    proximo_status_nome = dict(Pedido.STATUS_CHOICES).get(proximo_status) if proximo_status else None
    pode_cancelar = pedido.status in ["AGUARDANDO_PAGAMENTO", "EM_PREPARACAO"]

    motivo_bloqueio = None
    if not pode_cancelar:
        if pedido.status == "CANCELADO":
            motivo_bloqueio = "Pedido já cancelado."
        elif pedido.status == "ENTREGUE":
            motivo_bloqueio = "Pedido entregue. Cancelamento não permitido."
        elif pedido.status == "SAIU_PARA_ENTREGA":
            motivo_bloqueio = "Pedido saiu para entrega. Cancelamento não permitido."
        else:
            motivo_bloqueio = "Cancelamento permitido apenas para pedidos aguardando pagamento ou em preparação."

    historico = pedido.historico_status.all().order_by("criado_em", "pk")

    contexto = {
        "pedido": pedido,
        "proximo_status": proximo_status,
        "proximo_status_nome": proximo_status_nome,
        "pode_cancelar": pode_cancelar,
        "motivo_bloqueio": motivo_bloqueio,
        "historico": historico,
        "secao_painel": "pedidos",
    }
    return render(request, "painel/pedido_detalhe.html", contexto)


@staff_necessario
@require_POST
def pedido_avancar_status(request, numero):
    pedido = get_object_or_404(Pedido, numero=numero)
    proximo_status = PROXIMA_ETAPA.get(pedido.status)
    if not proximo_status:
        messages.error(request, f"Não há próxima etapa válida para o status atual ({pedido.get_status_display()}).")
        return redirect("painel:pedido_detalhe", numero=pedido.numero)

    try:
        pedido_service.alterar_status(pedido, proximo_status)
        messages.success(request, f"Status do pedido alterado para {pedido.get_status_display()}.")
    except (ErroPedido, ErroEstoque) as erro:
        messages.error(request, str(erro))

    return redirect("painel:pedido_detalhe", numero=pedido.numero)


@staff_necessario
@require_POST
def pedido_cancelar(request, numero):
    pedido = get_object_or_404(Pedido, numero=numero)
    motivo = request.POST.get("motivo", "").strip()

    if pedido.status not in ["AGUARDANDO_PAGAMENTO", "EM_PREPARACAO"]:
        messages.error(
            request,
            f"Cancelamento não permitido para o pedido no status {pedido.get_status_display()}. Apenas pedidos aguardando pagamento ou em preparação podem ser cancelados.",
        )
        return redirect("painel:pedido_detalhe", numero=pedido.numero)

    try:
        pedido_service.alterar_status(pedido, "CANCELADO", motivo=motivo)
        messages.success(request, f"Pedido {pedido.numero} cancelado com sucesso.")
    except ErroPedido as erro:
        messages.error(request, str(erro))

    return redirect("painel:pedido_detalhe", numero=pedido.numero)
