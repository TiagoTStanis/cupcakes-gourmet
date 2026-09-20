from django import forms
from django.utils.text import slugify

from catalogo.models import Categoria, Produto
from catalogo.validators import validar_imagem


def gerar_slug_unico_produto(nome, slug_informado="", produto_id=None):
    base = slugify(slug_informado) if slug_informado else slugify(nome)
    if not base:
        base = "cupcake"
    slug = base
    contador = 1
    qs = Produto.objects.all()
    if produto_id:
        qs = qs.exclude(pk=produto_id)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{contador}"
        contador += 1
    return slug


def gerar_slug_unico_categoria(nome, slug_informado="", categoria_id=None):
    base = slugify(slug_informado) if slug_informado else slugify(nome)
    if not base:
        base = "categoria"
    slug = base
    contador = 1
    qs = Categoria.objects.all()
    if categoria_id:
        qs = qs.exclude(pk=categoria_id)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{contador}"
        contador += 1
    return slug


class ProdutoForm(forms.ModelForm):
    slug = forms.SlugField(
        label="Slug",
        max_length=150,
        required=False,
        help_text="Gerado automaticamente a partir do nome se deixado em branco.",
    )

    class Meta:
        model = Produto
        fields = [
            "nome",
            "slug",
            "categoria",
            "descricao",
            "ingredientes",
            "alergenicos",
            "preco",
            "estoque",
            "imagem",
            "ativo",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "ingredientes": forms.Textarea(attrs={"rows": 3}),
            "alergenicos": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.all()
        if "ativo" in self.fields and not getattr(self.instance, "pk", None):
            self.fields["ativo"].initial = True

    def clean_imagem(self):
        imagem = self.cleaned_data.get("imagem")
        if imagem:
            validar_imagem(imagem)
        return imagem

    def clean(self):
        cleaned_data = super().clean()
        nome = cleaned_data.get("nome")
        slug = cleaned_data.get("slug")
        if nome:
            cleaned_data["slug"] = gerar_slug_unico_produto(
                nome=nome,
                slug_informado=slug,
                produto_id=self.instance.pk if getattr(self.instance, "pk", None) else None,
            )
        return cleaned_data

    def save(self, commit=True):
        instancia = super().save(commit=False)
        if "slug" in self.cleaned_data:
            instancia.slug = self.cleaned_data["slug"]
        if commit:
            instancia.save()
        return instancia


class CategoriaForm(forms.ModelForm):
    slug = forms.SlugField(
        label="Slug",
        max_length=100,
        required=False,
        help_text="Gerado automaticamente se deixado em branco.",
    )

    class Meta:
        model = Categoria
        fields = ["nome", "slug", "ativa"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "ativa" in self.fields and not getattr(self.instance, "pk", None):
            self.fields["ativa"].initial = True

    def clean(self):
        cleaned_data = super().clean()
        nome = cleaned_data.get("nome")
        slug = cleaned_data.get("slug")
        if nome:
            cleaned_data["slug"] = gerar_slug_unico_categoria(
                nome=nome,
                slug_informado=slug,
                categoria_id=self.instance.pk if getattr(self.instance, "pk", None) else None,
            )
        return cleaned_data

    def save(self, commit=True):
        instancia = super().save(commit=False)
        if "slug" in self.cleaned_data:
            instancia.slug = self.cleaned_data["slug"]
        if commit:
            instancia.save()
        return instancia
