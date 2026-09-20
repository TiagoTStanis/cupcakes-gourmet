from decimal import Decimal
import pytest

from catalogo.models import Categoria, Produto
from usuarios.models import Usuario


class ColecaoCategorias(list):
    def __getitem__(self, chave):
        if isinstance(chave, str):
            for item in self:
                if item.slug == chave or item.nome.lower() == chave.lower():
                    return item
            raise KeyError(chave)
        return super().__getitem__(chave)

    def __getattr__(self, nome):
        try:
            return self[nome]
        except KeyError:
            raise AttributeError(nome)


class ColecaoProdutos(list):
    def __getitem__(self, chave):
        if isinstance(chave, str):
            for item in self:
                if item.slug == chave or item.nome.lower() == chave.lower():
                    return item
            raise KeyError(chave)
        return super().__getitem__(chave)


@pytest.fixture
def usuario_cliente(db):
    return Usuario.objects.create_user("cliente@teste.com", "Cliente@123456", nome_completo="Marina Souza", email_confirmado=True)


@pytest.fixture
def usuario_admin(db):
    return Usuario.objects.create_superuser("admin@teste.com", "SenhaAdmin@321", nome_completo="Paulo Silva")


@pytest.fixture
def usuario_staff(db):
    return Usuario.objects.create_user(
        "staff@teste.com",
        "Staff@123456",
        nome_completo="Renata Staff",
        email_confirmado=True,
        is_staff=True,
    )


@pytest.fixture
def categorias(db):
    c1 = Categoria.objects.create(nome="Clássicos", slug="classicos", ativa=True)
    c2 = Categoria.objects.create(nome="Veganos", slug="veganos", ativa=True)
    c3 = Categoria.objects.create(nome="Temáticos", slug="tematicos", ativa=True)
    return ColecaoCategorias([c1, c2, c3])


@pytest.fixture
def produtos_com_estoque(db, categorias):
    p1 = Produto.objects.create(
        categoria=categorias["classicos"],
        nome="Cupcake de Chocolate Belga",
        slug="cupcake-de-chocolate-belga",
        descricao="Massa fofinha de cacau 70% com recheio cremoso.",
        ingredientes="Farinha de trigo, cacau em pó 70%, açúcar, ovos, manteiga.",
        alergenicos="Contém glúten, leite e ovos.",
        preco=Decimal("12.50"),
        estoque=15,
        total_vendas=80,
        ativo=True,
    )
    p2 = Produto.objects.create(
        categoria=categorias["classicos"],
        nome="Cupcake de Limão Siciliano",
        slug="cupcake-de-limao-siciliano",
        descricao="Massa aromatizada com raspas de limão e cobertura de merengue.",
        ingredientes="Farinha, limão siciliano, açúcar, ovos.",
        alergenicos="Contém glúten e ovos.",
        preco=Decimal("11.00"),
        estoque=8,
        total_vendas=120,
        ativo=True,
    )
    p3 = Produto.objects.create(
        categoria=categorias["veganos"],
        nome="Cupcake Vegano de Frutas Vermelhas",
        slug="cupcake-vegano-frutas-vermelhas",
        descricao="100% vegetal com recheio artesanal de frutas vermelhas.",
        ingredientes="Farinha de aveia, leite de amêndoas, frutas vermelhas, açúcar demerara.",
        alergenicos="Contém aveia e amêndoas.",
        preco=Decimal("14.00"),
        estoque=10,
        total_vendas=45,
        ativo=True,
    )
    return ColecaoProdutos([p1, p2, p3])


@pytest.fixture
def carrinho_com_itens(db, usuario_cliente, produtos_com_estoque):
    from carrinho.services import carrinho_service
    carrinho = carrinho_service.obter_carrinho(usuario_cliente)
    carrinho_service.adicionar(carrinho, produtos_com_estoque[0], quantidade=2)
    carrinho_service.adicionar(carrinho, produtos_com_estoque[1], quantidade=1)
    return carrinho


@pytest.fixture
def cupom_valido(db):
    from datetime import timedelta
    from django.utils import timezone
    from pedidos.models import Cupom

    return Cupom.objects.create(
        codigo="PROMO10",
        tipo="PERCENTUAL",
        valor=Decimal("10.00"),
        valor_minimo_pedido=Decimal("20.00"),
        data_validade=timezone.now() + timedelta(days=7),
        ativo=True,
    )


@pytest.fixture
def tabela_frete(db):
    from pedidos.dados_frete import carregar_tabela_frete

    carregar_tabela_frete()


