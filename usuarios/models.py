from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower


class GerenciadorUsuario(BaseUserManager):
    def create_user(self, email, password=None, **dados):
        if not email:
            raise ValueError("Informe o e-mail.")
        usuario = self.model(email=email.strip().lower(), **dados)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **dados):
        dados.setdefault("is_staff", True)
        dados.setdefault("is_superuser", True)
        dados.setdefault("email_confirmado", True)
        if not dados["is_staff"] or not dados["is_superuser"]:
            raise ValueError("O administrador precisa das permissões de acesso.")
        return self.create_user(email, password, **dados)


class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("e-mail", unique=True)
    nome_completo = models.CharField("nome completo", max_length=150)
    telefone = models.CharField(max_length=20, blank=True)
    email_confirmado = models.BooleanField(default=False)
    token_confirmacao = models.CharField(max_length=64, null=True, blank=True)
    token_recuperacao = models.CharField(max_length=64, null=True, blank=True)
    token_recuperacao_expira = models.DateTimeField(null=True, blank=True)
    tentativas_login_falhas = models.PositiveIntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = GerenciadorUsuario()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="usuario_email_sem_maiusculas")]
        verbose_name = "usuário"

    def __str__(self):
        return self.email


class Endereco(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="enderecos")
    cep = models.CharField("CEP", max_length=9)
    logradouro = models.CharField(max_length=150)
    numero = models.CharField("número", max_length=20)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=80)
    cidade = models.CharField(max_length=80)
    uf = models.CharField("UF", max_length=2)
    principal = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.logradouro}, {self.numero} — {self.cidade}/{self.uf}"
