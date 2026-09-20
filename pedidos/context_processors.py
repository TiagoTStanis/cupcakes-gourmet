from pedidos.models import Notificacao


def notificacoes_contexto(request):
    quantidade = 0
    if request.user.is_authenticated:
        quantidade = Notificacao.objects.filter(usuario=request.user, lida=False).count()
    return {"notificacoes_nao_lidas": quantidade}
