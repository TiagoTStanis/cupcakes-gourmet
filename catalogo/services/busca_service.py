import unicodedata
from catalogo.models import Categoria, Produto

MAPA_ORDENACAO = {
    "popularidade": ["-total_vendas", "-criado_em"],
    "menor_preco": ["preco", "nome"],
    "menor-preco": ["preco", "nome"],
    "preco_asc": ["preco", "nome"],
    "maior_preco": ["-preco", "nome"],
    "maior-preco": ["-preco", "nome"],
    "preco_desc": ["-preco", "nome"],
    "nome": ["nome"],
}


def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto_nfkd = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(caractere for caractere in texto_nfkd if not unicodedata.combining(caractere))
    return sem_acento.strip().lower()


def listar_categorias_ativas():
    return Categoria.objects.ativas().order_by("nome")


def listar_produtos(categoria_slug=None, ordenacao="popularidade"):
    qs = Produto.objects.ativos().filter(categoria__ativa=True).select_related("categoria")
    if categoria_slug:
        qs = qs.filter(categoria__slug=categoria_slug)
    criterios = MAPA_ORDENACAO.get(ordenacao, MAPA_ORDENACAO["popularidade"])
    return qs.order_by(*criterios)


def buscar_produtos(termo="", categoria_slug=None, ordenacao="popularidade"):
    qs = listar_produtos(categoria_slug=categoria_slug, ordenacao=ordenacao)
    if termo:
        termo_normalizado = normalizar_texto(termo)
        if termo_normalizado:
            qs = qs.filter(nome_busca__icontains=termo_normalizado)
    return qs
