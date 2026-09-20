from django.db import transaction
from django.shortcuts import get_object_or_404

from usuarios.models import Endereco


def atualizar_perfil(usuario, dados):
    usuario.nome_completo = dados["nome_completo"]
    usuario.telefone = dados["telefone"]
    usuario.save(update_fields=["nome_completo", "telefone"])


@transaction.atomic
def cadastrar_endereco(usuario, dados):
    if dados.get("principal"):
        usuario.enderecos.update(principal=False)
    return Endereco.objects.create(usuario=usuario, **dados)


def remover_endereco(usuario, endereco_id):
    endereco = get_object_or_404(Endereco, pk=endereco_id, usuario=usuario)
    endereco.delete()
