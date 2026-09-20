from django import forms

from usuarios.models import Endereco, Usuario
from usuarios.services.auth_service import validar_senha


class SenhaForm(forms.Form):
    senha = forms.CharField(label="Senha", strip=False, validators=[validar_senha], widget=forms.PasswordInput(
        attrs={"autocomplete": "new-password", "data-forca-senha": "", "aria-describedby": "forca-senha"},
    ))
    confirmar_senha = forms.CharField(label="Confirme a senha", strip=False, widget=forms.PasswordInput(
        attrs={"autocomplete": "new-password"},
    ))

    def clean(self):
        dados = super().clean()
        if dados.get("senha") and dados.get("senha") != dados.get("confirmar_senha"):
            self.add_error("confirmar_senha", "As senhas não coincidem.")
        return dados


class CadastroForm(SenhaForm):
    nome_completo = forms.CharField(label="Nome completo", max_length=150)
    email = forms.EmailField(label="E-mail")
    telefone = forms.CharField(label="Telefone", max_length=20, required=False)
    field_order = ["nome_completo", "email", "telefone", "senha", "confirmar_senha"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email


class LoginForm(forms.Form):
    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "username"}))
    senha = forms.CharField(label="Senha", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class RecuperacaoForm(forms.Form):
    email = forms.EmailField(label="E-mail")


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["nome_completo", "telefone"]


class EnderecoForm(forms.ModelForm):
    cep = forms.RegexField(regex=r"^\d{5}-?\d{3}$", label="CEP", error_messages={"invalid": "Informe um CEP com 8 números."})
    uf = forms.ChoiceField(label="UF", choices=[(uf, uf) for uf in (
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
        "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    )])

    class Meta:
        model = Endereco
        fields = ["cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf", "principal"]
