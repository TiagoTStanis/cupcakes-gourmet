from django.contrib import admin

from catalogo.models import Categoria, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ativa")
    list_filter = ("ativa",)
    search_fields = ("nome",)
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "estoque", "total_vendas", "ativo")
    list_filter = ("categoria", "ativo")
    search_fields = ("nome", "nome_busca")
    prepopulated_fields = {"slug": ("nome",)}
