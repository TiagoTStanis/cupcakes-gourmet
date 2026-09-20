from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from catalogo.validators import validar_imagem


class CategoriaQuerySet(models.QuerySet):
    def ativas(self):
        return self.filter(ativa=True)


class CategoriaManager(models.Manager):
    def get_queryset(self):
        return CategoriaQuerySet(self.model, using=self._db)

    def ativas(self):
        return self.get_queryset().ativas()


class Categoria(models.Model):
    nome = models.CharField("nome", max_length=100, unique=True)
    slug = models.SlugField("slug", max_length=100, unique=True)
    ativa = models.BooleanField("ativa", default=True)

    objects = CategoriaManager()

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        ordering = ["nome"]

    def save(self, *args, **kwargs):
        if not self.slug and self.nome:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class ProdutoQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)

    def delete(self):
        return self.update(ativo=False)


class ProdutoManager(models.Manager):
    def get_queryset(self):
        return ProdutoQuerySet(self.model, using=self._db)

    def ativos(self):
        return self.get_queryset().ativos()


class Produto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="produtos")
    nome = models.CharField("nome", max_length=150)
    slug = models.SlugField("slug", max_length=150, unique=True)
    descricao = models.TextField("descrição")
    ingredientes = models.TextField("ingredientes")
    alergenicos = models.TextField("alergênicos")
    preco = models.DecimalField("preço", max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    imagem = models.ImageField("imagem", upload_to="produtos/", blank=True, null=True, validators=[validar_imagem])
    estoque = models.PositiveIntegerField("estoque", default=0)
    total_vendas = models.PositiveIntegerField("total de vendas", default=0)
    ativo = models.BooleanField("ativo", default=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)
    nome_busca = models.CharField("nome para busca", max_length=150, blank=True, db_index=True)

    objects = ProdutoManager()

    class Meta:
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        ordering = ["-total_vendas", "-criado_em"]

    def delete(self, using=None, keep_parents=False):
        self.ativo = False
        self.save(update_fields=["ativo", "atualizado_em"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def save(self, *args, **kwargs):
        from catalogo.services.busca_service import normalizar_texto
        if self.nome:
            self.nome_busca = normalizar_texto(self.nome)
        if not self.slug and self.nome:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalogo:produto_detalhe", kwargs={"slug": self.slug})

    def __str__(self):
        return self.nome
