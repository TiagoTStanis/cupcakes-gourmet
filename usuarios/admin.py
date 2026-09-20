from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from usuarios.models import Endereco, Usuario


class CriacaoUsuarioForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email", "nome_completo")


class AlteracaoUsuarioForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = AlteracaoUsuarioForm
    add_form = CriacaoUsuarioForm
    ordering = ("email",)
    list_display = ("email", "nome_completo", "email_confirmado", "is_staff")
    search_fields = ("email", "nome_completo")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados", {"fields": ("nome_completo", "telefone", "email_confirmado")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"fields": ("email", "nome_completo", "password1", "password2")}),)


admin.site.register(Endereco)
