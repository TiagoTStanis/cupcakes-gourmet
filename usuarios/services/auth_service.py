import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Usuario


ERRO_LOGIN = "E-mail ou senha inválidos."
CONTA_NAO_ATIVADA = "Sua conta ainda não foi ativada. Verifique o link enviado ao seu e-mail."
RESPOSTA_RECUPERACAO = "Se o e-mail informado estiver cadastrado, as instruções foram enviadas."


def validar_senha(senha):
    if len(senha) < 8 or not any(letra.isupper() for letra in senha) or not any(letra.isdigit() for letra in senha):
        raise ValidationError("Use pelo menos 8 caracteres, uma letra maiúscula e um número.")


class ValidadorSenha:
    def validate(self, password, user=None):
        validar_senha(password)

    def get_help_text(self):
        return "Use pelo menos 8 caracteres, uma letra maiúscula e um número."


def resumo_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def enviar_link(usuario, token, rota, assunto, url_base):
    link = url_base.rstrip("/") + reverse(rota, args=[token])
    send_mail(assunto, f"Acesse o link: {link}", settings.DEFAULT_FROM_EMAIL, [usuario.email])
    return link


def cadastrar_usuario(nome_completo, email, senha, telefone="", url_base="http://localhost:8000"):
    validar_senha(senha)
    email = email.strip().lower()
    validate_email(email)
    token = secrets.token_urlsafe(32)
    try:
        with transaction.atomic():
            usuario = Usuario.objects.create_user(
                email, senha, nome_completo=nome_completo, telefone=telefone,
                token_confirmacao=resumo_token(token),
            )
    except IntegrityError:
        raise ValidationError("Este e-mail já está cadastrado.") from None
    link = enviar_link(usuario, token, "usuarios:ativar", "Ative sua conta", url_base)
    return usuario, link


def ativar_conta(token):
    alterados = Usuario.objects.filter(token_confirmacao=resumo_token(token), is_active=True).update(
        email_confirmado=True, token_confirmacao=None,
    )
    if not alterados:
        raise ValidationError("Link de ativação inválido ou já utilizado.")


def autenticar_usuario(email, senha):
    agora = timezone.now()
    usuario = Usuario.objects.filter(email__iexact=email.strip()).first()
    if usuario is None:
        make_password(senha)
        raise ValidationError(ERRO_LOGIN)
    if not usuario.is_active or (usuario.bloqueado_ate and usuario.bloqueado_ate > agora):
        raise ValidationError(ERRO_LOGIN)
    if usuario.bloqueado_ate:
        Usuario.objects.filter(pk=usuario.pk).update(bloqueado_ate=None, tentativas_login_falhas=0)
    if not usuario.check_password(senha):
        Usuario.objects.filter(pk=usuario.pk).update(tentativas_login_falhas=F("tentativas_login_falhas") + 1)
        Usuario.objects.filter(pk=usuario.pk, tentativas_login_falhas__gte=3, bloqueado_ate=None).update(
            bloqueado_ate=agora + timedelta(minutes=15),
        )
        raise ValidationError(ERRO_LOGIN)
    Usuario.objects.filter(pk=usuario.pk).update(tentativas_login_falhas=0, bloqueado_ate=None)
    if not usuario.email_confirmado:
        raise ValidationError(CONTA_NAO_ATIVADA)
    usuario.refresh_from_db()
    return usuario


def solicitar_recuperacao(email, url_base="http://localhost:8000"):
    usuario = Usuario.objects.filter(email__iexact=email.strip(), is_active=True).first()
    if not usuario:
        return None
    token = secrets.token_urlsafe(32)
    usuario.token_recuperacao = resumo_token(token)
    usuario.token_recuperacao_expira = timezone.now() + timedelta(minutes=60)
    usuario.save(update_fields=["token_recuperacao", "token_recuperacao_expira"])
    return enviar_link(usuario, token, "usuarios:redefinir", "Redefina sua senha", url_base)


def recuperacao_valida(token):
    return Usuario.objects.filter(
        token_recuperacao=resumo_token(token), token_recuperacao_expira__gt=timezone.now(), is_active=True,
    ).exists()


def redefinir_senha(token, senha):
    validar_senha(senha)
    # A atualização condicional consome o token uma única vez, inclusive em requisições concorrentes.
    alterados = Usuario.objects.filter(
        token_recuperacao=resumo_token(token), token_recuperacao_expira__gt=timezone.now(), is_active=True,
    ).update(password=make_password(senha), token_recuperacao=None, token_recuperacao_expira=None,
             tentativas_login_falhas=0, bloqueado_ate=None)
    if not alterados:
        raise ValidationError("Link de recuperação inválido, expirado ou já utilizado.")
