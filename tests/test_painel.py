from datetime import timedelta
from decimal import Decimal
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from catalogo.models import Categoria, Produto
from pedidos.models import HistoricoStatus, ItemPedido, Notificacao, Pedido, ReservaEstoque
from pedidos.services import pedido_service
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def _criar_imagem_arquivo(formato="JPEG", nome="cupcake.jpg"):
    buffer = io.BytesIO()
    img = Image.new("RGB", (60, 60), color="pink")
    img.save(buffer, format=formato)
    buffer.seek(0)
    tipo = "image/jpeg" if formato == "JPEG" else "image/png"
    return SimpleUploadedFile(nome, buffer.getvalue(), content_type=tipo)


@pytest.fixture
def pedido_teste(usuario_cliente, produtos_com_estoque):
    pedido = Pedido.objects.create(
        numero="CG-TESTE-01",
        usuario=usuario_cliente,
        endereco_entrega="Rua das Flores, 100\nCentro — Cascavel/PR\nCEP 85801-000",
        subtotal=Decimal("25.00"),
        valor_frete=Decimal("10.00"),
        valor_total=Decimal("35.00"),
        forma_pagamento="PIX",
        status="AGUARDANDO_PAGAMENTO",
        pix_expira_em=timezone.now() + timedelta(minutes=30),
    )
    produto = produtos_com_estoque[0]
    ItemPedido.objects.create(
        pedido=pedido,
        produto=produto,
        nome_produto=produto.nome,
        preco_unitario=produto.preco,
        quantidade=2,
        subtotal=Decimal("25.00"),
    )
    return pedido


def test_visitante_redirecionado_para_login_em_todas_as_rotas_do_painel(client, produtos_com_estoque, pedido_teste):
    produto = produtos_com_estoque[0]
    categoria = produto.categoria
    rotas = [
        reverse("painel:inicio"),
        reverse("painel:produtos_lista"),
        reverse("painel:produto_criar"),
        reverse("painel:produto_editar", args=[produto.pk]),
        reverse("painel:categorias_lista"),
        reverse("painel:categoria_criar"),
        reverse("painel:categoria_editar", args=[categoria.pk]),
        reverse("painel:pedidos_lista"),
        reverse("painel:pedido_detalhe", args=[pedido_teste.numero]),
    ]
    for rota in rotas:
        resposta = client.get(rota)
        assert resposta.status_code == 302
        assert reverse("usuarios:login") in resposta["Location"]
        assert "next=" in resposta["Location"]


def test_cliente_comum_recebe_403_em_todas_as_rotas_do_painel(client, usuario_cliente, produtos_com_estoque, pedido_teste):
    client.force_login(usuario_cliente)
    produto = produtos_com_estoque[0]
    categoria = produto.categoria
    rotas = [
        reverse("painel:inicio"),
        reverse("painel:produtos_lista"),
        reverse("painel:produto_criar"),
        reverse("painel:produto_editar", args=[produto.pk]),
        reverse("painel:categorias_lista"),
        reverse("painel:categoria_criar"),
        reverse("painel:categoria_editar", args=[categoria.pk]),
        reverse("painel:pedidos_lista"),
        reverse("painel:pedido_detalhe", args=[pedido_teste.numero]),
    ]
    for rota in rotas:
        resposta = client.get(rota)
        assert resposta.status_code == 403
        assert "Acesso Negado" in resposta.content.decode()


def test_usuario_staff_acessa_todas_as_rotas_do_painel(client, usuario_staff, produtos_com_estoque, pedido_teste):
    client.force_login(usuario_staff)
    produto = produtos_com_estoque[0]
    categoria = produto.categoria
    rotas = [
        reverse("painel:inicio"),
        reverse("painel:produtos_lista"),
        reverse("painel:produto_criar"),
        reverse("painel:produto_editar", args=[produto.pk]),
        reverse("painel:categorias_lista"),
        reverse("painel:categoria_criar"),
        reverse("painel:categoria_editar", args=[categoria.pk]),
        reverse("painel:pedidos_lista"),
        reverse("painel:pedido_detalhe", args=[pedido_teste.numero]),
    ]
    for rota in rotas:
        resposta = client.get(rota)
        assert resposta.status_code == 200


def test_link_painel_visivel_apenas_para_staff(client, usuario_staff, usuario_cliente):
    resposta_visitante = client.get(reverse("inicio"))
    assert "cabecalho-painel-link" not in resposta_visitante.content.decode()

    client.force_login(usuario_cliente)
    resposta_cliente = client.get(reverse("inicio"))
    assert "cabecalho-painel-link" not in resposta_cliente.content.decode()

    client.force_login(usuario_staff)
    resposta_staff = client.get(reverse("inicio"))
    assert "cabecalho-painel-link" in resposta_staff.content.decode()
    assert reverse("painel:inicio") in resposta_staff.content.decode()


def test_criar_produto_valido_aparece_na_vitrine_imediatamente(client, usuario_staff, categorias):
    client.force_login(usuario_staff)
    foto = _criar_imagem_arquivo(formato="JPEG", nome="redvelvet.jpg")
    dados = {
        "nome": "Cupcake Red Velvet Especial",
        "categoria": categorias["classicos"].pk,
        "descricao": "Massa vermelha aveludada com cobertura de cream cheese.",
        "ingredientes": "Farinha de trigo, cacau, corante natural, manteiga, cream cheese.",
        "alergenicos": "Contém glúten e derivados de leite.",
        "preco": "14.50",
        "estoque": "15",
        "imagem": foto,
        "ativo": "on",
    }
    resposta = client.post(reverse("painel:produto_criar"), data=dados)
    assert resposta.status_code == 302
    assert resposta["Location"] == reverse("painel:produtos_lista")

    produto = Produto.objects.get(nome="Cupcake Red Velvet Especial")
    assert produto.slug == "cupcake-red-velvet-especial"
    assert produto.ativo is True

    # Vitrine publica deve exibir o novo cupcake imediatamente
    vitrine = client.get(reverse("catalogo:vitrine"))
    assert "Cupcake Red Velvet Especial" in vitrine.content.decode()


def test_campo_obrigatorio_vazio_mostra_erro_por_campo_e_nao_salva(client, usuario_staff, categorias):
    client.force_login(usuario_staff)
    qtd_inicial = Produto.objects.count()
    dados = {
        "nome": "",
        "categoria": categorias["classicos"].pk,
        "descricao": "Uma descricao qualquer.",
        "ingredientes": "",
        "alergenicos": "Contém leite.",
        "preco": "",
        "estoque": "10",
    }
    resposta = client.post(reverse("painel:produto_criar"), data=dados)
    assert resposta.status_code == 200
    assert Produto.objects.count() == qtd_inicial

    formulario = resposta.context["form"]
    assert "nome" in formulario.errors
    assert "preco" in formulario.errors
    assert "ingredientes" in formulario.errors

    # Mantem os dados digitados nos demais campos
    conteudo = resposta.content.decode()
    assert "Uma descricao qualquer." in conteudo
    assert "Contém leite." in conteudo


def test_imagem_invalida_extensao_e_tamanho_mostram_erro_e_nao_salvam(client, usuario_staff, categorias):
    client.force_login(usuario_staff)
    qtd_inicial = Produto.objects.count()

    # Extensao invalida
    arquivo_txt = SimpleUploadedFile("imagem.txt", b"arquivo de texto", content_type="text/plain")
    dados_txt = {
        "nome": "Cupcake Teste Invalido",
        "categoria": categorias["classicos"].pk,
        "descricao": "Descricao teste",
        "ingredientes": "Ingredientes",
        "alergenicos": "Nenhum",
        "preco": "10.00",
        "estoque": "5",
        "imagem": arquivo_txt,
    }
    resposta_txt = client.post(reverse("painel:produto_criar"), data=dados_txt)
    assert resposta_txt.status_code == 200
    assert "imagem" in resposta_txt.context["form"].errors
    assert Produto.objects.count() == qtd_inicial

    # Imagem maior que 5MB
    arquivo_pesado = SimpleUploadedFile(
        "grande.jpg",
        b"X" * (6 * 1024 * 1024),
        content_type="image/jpeg",
    )
    dados_pesados = dict(dados_txt)
    dados_pesados["imagem"] = arquivo_pesado
    resposta_pesada = client.post(reverse("painel:produto_criar"), data=dados_pesados)
    assert resposta_pesada.status_code == 200
    assert "imagem" in resposta_pesada.context["form"].errors
    assert Produto.objects.count() == qtd_inicial


def test_editar_produto(client, usuario_staff, produtos_com_estoque):
    client.force_login(usuario_staff)
    produto = produtos_com_estoque[0]
    dados = {
        "nome": "Cupcake de Chocolate Meio Amargo",
        "slug": produto.slug,
        "categoria": produto.categoria.pk,
        "descricao": "Descricao atualizada com cacau 80%.",
        "ingredientes": produto.ingredientes,
        "alergenicos": produto.alergenicos,
        "preco": "16.00",
        "estoque": "30",
        "ativo": "on",
    }
    resposta = client.post(reverse("painel:produto_editar", args=[produto.pk]), data=dados)
    assert resposta.status_code == 302

    produto.refresh_from_db()
    assert produto.nome == "Cupcake de Chocolate Meio Amargo"
    assert produto.preco == Decimal("16.00")
    assert produto.estoque == 30


def test_desativar_mantem_no_banco_some_da_vitrine_mas_permanece_em_pedidos_antigos(client, usuario_staff, produtos_com_estoque, pedido_teste):
    client.force_login(usuario_staff)
    produto = produtos_com_estoque[0]
    assert produto.ativo is True

    item = pedido_teste.itens.first()
    assert item.produto_id == produto.id

    resposta = client.post(reverse("painel:produto_desativar", args=[produto.pk]))
    assert resposta.status_code == 302

    # Mantem no banco de dados com ativo=False
    produto.refresh_from_db()
    assert produto.ativo is False
    assert Produto.objects.filter(pk=produto.pk).exists()

    # Some da vitrine publica
    vitrine = client.get(reverse("catalogo:vitrine"))
    assert f"/produto/{produto.slug}/" not in vitrine.content.decode()

    # Permanece referenciado nos itens do pedido anterior
    item.refresh_from_db()
    assert item.produto == produto
    assert item.nome_produto == produto.nome


def test_reativar_produto_volta_para_vitrine(client, usuario_staff, produtos_com_estoque):
    client.force_login(usuario_staff)
    produto = produtos_com_estoque[0]
    produto.ativo = False
    produto.save()

    resposta = client.post(reverse("painel:produto_reativar", args=[produto.pk]))
    assert resposta.status_code == 302

    produto.refresh_from_db()
    assert produto.ativo is True

    vitrine = client.get(reverse("catalogo:vitrine"))
    assert produto.nome in vitrine.content.decode()


def test_slug_duplicado_tratado_com_sufixo_unico(client, usuario_staff, categorias):
    client.force_login(usuario_staff)
    dados1 = {
        "nome": "Cupcake de Morango",
        "categoria": categorias["classicos"].pk,
        "descricao": "Descricao 1",
        "ingredientes": "Ingredientes 1",
        "alergenicos": "Leite",
        "preco": "10.00",
        "estoque": "10",
        "ativo": "on",
    }
    client.post(reverse("painel:produto_criar"), data=dados1)
    p1 = Produto.objects.get(nome="Cupcake de Morango")
    assert p1.slug == "cupcake-de-morango"

    # Criando outro com mesmo nome e sem slug informado
    dados2 = dict(dados1)
    dados2["descricao"] = "Descricao 2"
    client.post(reverse("painel:produto_criar"), data=dados2)
    p2 = Produto.objects.exclude(pk=p1.pk).get(nome="Cupcake de Morango")
    assert p2.slug == "cupcake-de-morango-1"

    # Criando com slug explicito ja existente
    dados3 = dict(dados1)
    dados3["slug"] = "cupcake-de-morango"
    client.post(reverse("painel:produto_criar"), data=dados3)
    p3 = Produto.objects.exclude(pk__in=[p1.pk, p2.pk]).get(nome="Cupcake de Morango")
    assert p3.slug == "cupcake-de-morango-2"


def test_filtros_pedidos_por_status_periodo_e_cliente(client, usuario_staff, usuario_cliente):
    client.force_login(usuario_staff)
    outro_usuario = Usuario.objects.create_user(
        "outro@teste.com",
        "Outro@123456",
        nome_completo="Carlos Ferreira",
        email_confirmado=True,
    )
    hoje = timezone.localdate()
    ontem = hoje - timedelta(days=1)

    p1 = Pedido.objects.create(
        numero="CG-FILTRO-01",
        usuario=usuario_cliente,
        endereco_entrega="Endereco 1",
        subtotal=Decimal("20.00"),
        valor_frete=Decimal("5.00"),
        valor_total=Decimal("25.00"),
        forma_pagamento="PIX",
        status="AGUARDANDO_PAGAMENTO",
    )
    p2 = Pedido.objects.create(
        numero="CG-FILTRO-02",
        usuario=outro_usuario,
        endereco_entrega="Endereco 2",
        subtotal=Decimal("30.00"),
        valor_frete=Decimal("5.00"),
        valor_total=Decimal("35.00"),
        forma_pagamento="CARTAO",
        status="EM_PREPARACAO",
    )
    p3 = Pedido.objects.create(
        numero="CG-FILTRO-03",
        usuario=usuario_cliente,
        endereco_entrega="Endereco 3",
        subtotal=Decimal("40.00"),
        valor_frete=Decimal("0.00"),
        valor_total=Decimal("40.00"),
        forma_pagamento="CARTAO",
        status="ENTREGUE",
    )
    # Ajusta data de criacao do p3 para ontem
    Pedido.objects.filter(pk=p3.pk).update(criado_em=timezone.now() - timedelta(days=1))

    # Filtro por status
    resp_status = client.get(reverse("painel:pedidos_lista") + "?status=AGUARDANDO_PAGAMENTO")
    pedidos_status = list(resp_status.context["pedidos"])
    assert p1 in pedidos_status
    assert p2 not in pedidos_status
    assert p3 not in pedidos_status

    # Filtro por cliente (nome ou email)
    resp_cliente = client.get(reverse("painel:pedidos_lista") + "?cliente=Carlos")
    pedidos_cliente = list(resp_cliente.context["pedidos"])
    assert p2 in pedidos_cliente
    assert p1 not in pedidos_cliente

    resp_email = client.get(reverse("painel:pedidos_lista") + "?cliente=cliente@teste.com")
    pedidos_email = list(resp_email.context["pedidos"])
    assert p1 in pedidos_email and p3 in pedidos_email
    assert p2 not in pedidos_email

    # Filtro por periodo
    resp_periodo = client.get(
        reverse("painel:pedidos_lista") + f"?data_inicio={hoje.isoformat()}&data_fim={hoje.isoformat()}"
    )
    pedidos_periodo = list(resp_periodo.context["pedidos"])
    assert p1 in pedidos_periodo and p2 in pedidos_periodo
    assert p3 not in pedidos_periodo

    # Filtros combinados
    resp_combinado = client.get(
        reverse("painel:pedidos_lista") + f"?status=AGUARDANDO_PAGAMENTO&cliente=Marina"
    )
    pedidos_comb = list(resp_combinado.context["pedidos"])
    assert pedidos_comb == [p1]


def test_avancar_status_gera_historico_e_notificacao(client, usuario_staff, pedido_teste):
    client.force_login(usuario_staff)
    assert pedido_teste.status == "AGUARDANDO_PAGAMENTO"

    resposta = client.post(reverse("painel:pedido_avancar_status", args=[pedido_teste.numero]))
    assert resposta.status_code == 302
    assert resposta["Location"] == reverse("painel:pedido_detalhe", args=[pedido_teste.numero])

    pedido_teste.refresh_from_db()
    assert pedido_teste.status == "PAGAMENTO_CONFIRMADO"
    assert pedido_teste.historico_status.filter(status="PAGAMENTO_CONFIRMADO").exists()

    notificacao = Notificacao.objects.filter(pedido=pedido_teste).latest("criada_em")
    assert notificacao.usuario == pedido_teste.usuario
    assert notificacao.titulo == "Pagamento confirmado"

    # Avanca para a etapa seguinte: EM_PREPARACAO
    client.post(reverse("painel:pedido_avancar_status", args=[pedido_teste.numero]))
    pedido_teste.refresh_from_db()
    assert pedido_teste.status == "EM_PREPARACAO"


def test_cancelar_em_aguardando_pagamento_e_em_preparacao_repoe_estoque_uma_unica_vez(client, usuario_staff, pedido_teste):
    client.force_login(usuario_staff)
    produto = pedido_teste.itens.first().produto
    estoque_original = produto.estoque

    # Caso 1: AGUARDANDO_PAGAMENTO (nao houve baixa definitiva de estoque)
    assert not pedido_teste.estoque_baixado
    resposta = client.post(
        reverse("painel:pedido_cancelar", args=[pedido_teste.numero]),
        data={"motivo": "Cliente solicitou cancelamento"},
    )
    assert resposta.status_code == 302
    pedido_teste.refresh_from_db()
    produto.refresh_from_db()
    assert pedido_teste.status == "CANCELADO"
    assert produto.estoque == estoque_original
    assert "Cliente solicitou cancelamento" in Notificacao.objects.latest("criada_em").mensagem

    # Caso 2: EM_PREPARACAO (houve baixa definitiva ao confirmar pagamento)
    pedido2 = Pedido.objects.create(
        numero="CG-PREPARACAO-01",
        usuario=pedido_teste.usuario,
        endereco_entrega=pedido_teste.endereco_entrega,
        subtotal=Decimal("25.00"),
        valor_frete=Decimal("10.00"),
        valor_total=Decimal("35.00"),
        forma_pagamento="CARTAO",
        status="AGUARDANDO_PAGAMENTO",
    )
    ItemPedido.objects.create(
        pedido=pedido2,
        produto=produto,
        nome_produto=produto.nome,
        preco_unitario=produto.preco,
        quantidade=3,
        subtotal=Decimal("37.50"),
    )
    # Confirma e avanca para preparacao (baixa estoque)
    pedido_service.alterar_status(pedido2, "PAGAMENTO_CONFIRMADO")
    pedido_service.alterar_status(pedido2, "EM_PREPARACAO")
    produto.refresh_from_db()
    assert produto.estoque == estoque_original - 3
    assert pedido2.estoque_baixado is True

    # Cancelar pelo painel repoe o estoque de volta
    client.post(
        reverse("painel:pedido_cancelar", args=[pedido2.numero]),
        data={"motivo": "Falta de matéria-prima"},
    )
    pedido2.refresh_from_db()
    produto.refresh_from_db()
    assert pedido2.status == "CANCELADO"
    assert produto.estoque == estoque_original

    # Tentativa de cancelar novamente nao repoe mais estoque
    client.post(reverse("painel:pedido_cancelar", args=[pedido2.numero]))
    produto.refresh_from_db()
    assert produto.estoque == estoque_original


def test_cancelar_em_saiu_para_entrega_e_entregue_e_bloqueado(client, usuario_staff, pedido_teste):
    client.force_login(usuario_staff)

    # Coloca o pedido em SAIU_PARA_ENTREGA
    pedido_service.alterar_status(pedido_teste, "PAGAMENTO_CONFIRMADO")
    pedido_service.alterar_status(pedido_teste, "EM_PREPARACAO")
    pedido_service.alterar_status(pedido_teste, "SAIU_PARA_ENTREGA")
    pedido_teste.refresh_from_db()

    # Na pagina de detalhe, botao de cancelar esta desabilitado e com explicacao
    detalhe = client.get(reverse("painel:pedido_detalhe", args=[pedido_teste.numero]))
    conteudo = detalhe.content.decode()
    assert "disabled" in conteudo
    assert "Pedido saiu para entrega" in conteudo

    # Tentativa de POST para cancelar e rejeitada
    resposta = client.post(reverse("painel:pedido_cancelar", args=[pedido_teste.numero]))
    assert resposta.status_code == 302
    pedido_teste.refresh_from_db()
    assert pedido_teste.status == "SAIU_PARA_ENTREGA"

    # Coloca em ENTREGUE
    pedido_service.alterar_status(pedido_teste, "ENTREGUE")
    detalhe_entregue = client.get(reverse("painel:pedido_detalhe", args=[pedido_teste.numero]))
    conteudo_entregue = detalhe_entregue.content.decode()
    assert "Pedido entregue" in conteudo_entregue

    client.post(reverse("painel:pedido_cancelar", args=[pedido_teste.numero]))
    pedido_teste.refresh_from_db()
    assert pedido_teste.status == "ENTREGUE"


def test_acoes_de_escrita_exigem_metodo_post(client, usuario_staff, produtos_com_estoque, pedido_teste):
    client.force_login(usuario_staff)
    produto = produtos_com_estoque[0]
    categoria = produto.categoria

    rotas_escrita = [
        reverse("painel:produto_desativar", args=[produto.pk]),
        reverse("painel:produto_reativar", args=[produto.pk]),
        reverse("painel:categoria_desativar", args=[categoria.pk]),
        reverse("painel:categoria_reativar", args=[categoria.pk]),
        reverse("painel:pedido_avancar_status", args=[pedido_teste.numero]),
        reverse("painel:pedido_cancelar", args=[pedido_teste.numero]),
    ]
    for rota in rotas_escrita:
        resposta = client.get(rota)
        assert resposta.status_code == 405


def test_paginacao_de_dez_itens_por_pagina(client, usuario_staff, categorias, usuario_cliente):
    client.force_login(usuario_staff)
    cat = categorias["classicos"]

    # Cria 15 produtos
    for i in range(15):
        Produto.objects.create(
            categoria=cat,
            nome=f"Cupcake Paginado {i+1:02d}",
            slug=f"cupcake-paginado-{i+1:02d}",
            descricao="Descricao",
            ingredientes="Ingredientes",
            alergenicos="Nenhum",
            preco=Decimal("10.00"),
            estoque=10,
        )

    resp_prod_p1 = client.get(reverse("painel:produtos_lista"))
    assert resp_prod_p1.context["pagina"].paginator.per_page == 10
    assert len(resp_prod_p1.context["produtos"]) == 10
    assert resp_prod_p1.context["pagina"].has_next()

    resp_prod_p2 = client.get(reverse("painel:produtos_lista") + "?pagina=2")
    # 15 produtos no total: 10 na primeira pagina e 5 na segunda
    assert len(resp_prod_p2.context["produtos"]) == 5

    # Cria 15 pedidos
    for i in range(15):
        Pedido.objects.create(
            numero=f"CG-PAG-{i+1:02d}",
            usuario=usuario_cliente,
            endereco_entrega="Endereco",
            subtotal=Decimal("20.00"),
            valor_frete=Decimal("10.00"),
            valor_total=Decimal("30.00"),
            forma_pagamento="PIX",
            status="AGUARDANDO_PAGAMENTO",
        )

    resp_ped_p1 = client.get(reverse("painel:pedidos_lista"))
    assert resp_ped_p1.context["pagina"].paginator.per_page == 10
    assert len(resp_ped_p1.context["pedidos"]) == 10
    assert resp_ped_p1.context["pagina"].has_next()

    resp_ped_p2 = client.get(reverse("painel:pedidos_lista") + "?pagina=2")
    assert len(resp_ped_p2.context["pedidos"]) == 5


def test_categorias_crud_e_ativar_desativar(client, usuario_staff):
    client.force_login(usuario_staff)

    # Criar categoria
    resp_criar = client.post(
        reverse("painel:categoria_criar"),
        data={"nome": "Especiais de Natal", "ativa": "on"},
    )
    assert resp_criar.status_code == 302
    cat = Categoria.objects.get(nome="Especiais de Natal")
    assert cat.slug == "especiais-de-natal"
    assert cat.ativa is True

    # Editar categoria
    resp_editar = client.post(
        reverse("painel:categoria_editar", args=[cat.pk]),
        data={"nome": "Especiais de Fim de Ano", "slug": cat.slug, "ativa": "on"},
    )
    assert resp_editar.status_code == 302
    cat.refresh_from_db()
    assert cat.nome == "Especiais de Fim de Ano"

    # Desativar categoria
    resp_desativar = client.post(reverse("painel:categoria_desativar", args=[cat.pk]))
    assert resp_desativar.status_code == 302
    cat.refresh_from_db()
    assert cat.ativa is False

    # Reativar categoria
    resp_reativar = client.post(reverse("painel:categoria_reativar", args=[cat.pk]))
    assert resp_reativar.status_code == 302
    cat.refresh_from_db()
    assert cat.ativa is True
