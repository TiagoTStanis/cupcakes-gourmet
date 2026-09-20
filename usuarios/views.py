from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as iniciar_sessao, logout as encerrar_sessao
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST

from usuarios.forms import CadastroForm, EnderecoForm, LoginForm, PerfilForm, RecuperacaoForm, SenhaForm
from usuarios.services import auth_service, perfil_service


@sensitive_post_parameters("senha", "confirmar_senha")
@require_http_methods(["GET", "POST"])
def cadastro(request):
    formulario = CadastroForm(request.POST if request.method == "POST" else None)
    link = None
    if request.method == "POST" and formulario.is_valid():
        dados = formulario.cleaned_data.copy()
        dados.pop("confirmar_senha")
        try:
            usuario, link = auth_service.cadastrar_usuario(**dados, url_base=request.build_absolute_uri("/"))
        except ValidationError as erro:
            formulario.add_error(None, erro)
        else:
            messages.success(request, "Cadastro concluído. Acesse o link enviado ao seu e-mail para ativar sua conta.")
            formulario = CadastroForm()
    return render(request, "usuarios/cadastro.html", {"formulario": formulario, "link_demo": link if settings.MODO_DEMO else None})


@sensitive_post_parameters("senha")
@require_http_methods(["GET", "POST"])
def login(request):
    formulario = LoginForm(request.POST if request.method == "POST" else None)
    proxima = request.POST.get("next", request.GET.get("next", ""))
    if request.method == "POST" and formulario.is_valid():
        try:
            usuario = auth_service.autenticar_usuario(**formulario.cleaned_data)
        except ValidationError as erro:
            formulario.add_error(None, erro)
        else:
            iniciar_sessao(request, usuario, backend="usuarios.backends.AutenticacaoEmail")
            if proxima and url_has_allowed_host_and_scheme(proxima, {request.get_host()}, require_https=request.is_secure()):
                return redirect(proxima)
            return redirect("usuarios:perfil")
    return render(request, "usuarios/login.html", {"formulario": formulario, "proxima": proxima})


@require_POST
def logout(request):
    encerrar_sessao(request)
    messages.success(request, "Você saiu da sua conta.")
    return redirect("inicio")


@require_http_methods(["GET", "POST"])
def ativar(request, token):
    if request.method == "POST":
        try:
            auth_service.ativar_conta(token)
        except ValidationError as erro:
            messages.error(request, erro.messages[0])
        else:
            messages.success(request, "Conta ativada. Você já pode entrar.")
        return redirect("usuarios:login")
    return render(request, "usuarios/ativar.html")


@require_http_methods(["GET", "POST"])
def esqueci_senha(request):
    formulario = RecuperacaoForm(request.POST if request.method == "POST" else None)
    link = None
    if request.method == "POST" and formulario.is_valid():
        link = auth_service.solicitar_recuperacao(formulario.cleaned_data["email"], request.build_absolute_uri("/"))
        messages.success(request, auth_service.RESPOSTA_RECUPERACAO)
        formulario = RecuperacaoForm()
    return render(request, "usuarios/esqueci_senha.html", {"formulario": formulario, "link_demo": link if settings.MODO_DEMO else None})


@sensitive_post_parameters("senha", "confirmar_senha")
@require_http_methods(["GET", "POST"])
def redefinir(request, token):
    formulario = SenhaForm(request.POST if request.method == "POST" else None)
    valido = auth_service.recuperacao_valida(token)
    if request.method == "POST" and formulario.is_valid():
        try:
            auth_service.redefinir_senha(token, formulario.cleaned_data["senha"])
        except ValidationError as erro:
            formulario.add_error(None, erro)
        else:
            messages.success(request, "Senha atualizada. Entre com sua nova senha.")
            return redirect("usuarios:login")
    return render(request, "usuarios/redefinir.html", {"formulario": formulario, "valido": valido})


@login_required
@require_http_methods(["GET", "POST"])
def perfil(request):
    formulario = PerfilForm(instance=request.user)
    endereco_form = EnderecoForm()
    if request.method == "POST":
        if request.POST.get("acao") == "endereco":
            endereco_form = EnderecoForm(request.POST)
            if endereco_form.is_valid():
                perfil_service.cadastrar_endereco(request.user, endereco_form.cleaned_data)
                messages.success(request, "Endereço cadastrado.")
                return redirect("usuarios:perfil")
        else:
            formulario = PerfilForm(request.POST, instance=request.user)
            if formulario.is_valid():
                perfil_service.atualizar_perfil(request.user, formulario.cleaned_data)
                messages.success(request, "Dados atualizados.")
                return redirect("usuarios:perfil")
    return render(request, "usuarios/perfil.html", {
        "formulario": formulario, "endereco_form": endereco_form,
        "enderecos": request.user.enderecos.order_by("-principal", "pk"),
    })


@login_required
@require_POST
def remover_endereco(request, endereco_id):
    perfil_service.remover_endereco(request.user, endereco_id)
    messages.success(request, "Endereço removido.")
    return redirect("usuarios:perfil")
