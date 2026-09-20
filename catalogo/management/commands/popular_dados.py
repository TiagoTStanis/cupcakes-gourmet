import io
import os
import secrets
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw

from catalogo.models import Categoria, Produto
from pedidos.dados_frete import carregar_tabela_frete
from pedidos.models import Cupom, CupomUso, HistoricoStatus, ItemPedido, Notificacao, Pedido, ReservaEstoque
from usuarios.models import Endereco, Usuario


def desenhar_cupcake(slug, cor_cobertura, tipo_detalhe):
    img = Image.new("RGB", (600, 600), color=(250, 246, 242))
    draw = ImageDraw.Draw(img)

    # Sombra suave na base
    draw.ellipse([180, 500, 420, 535], fill=(225, 220, 215))

    # Forminha trapezoidal
    pontos_forminha = [(190, 360), (410, 360), (375, 510), (225, 510)]
    draw.polygon(pontos_forminha, fill=(238, 224, 206))

    # Plissado da forminha
    linhas = 9
    for i in range(1, linhas):
        t = i / linhas
        x_topo = 190 + t * (410 - 190)
        x_base = 225 + t * (375 - 225)
        draw.line([(x_topo, 360), (x_base, 510)], fill=(215, 196, 172), width=3)

    # Borda da forminha
    draw.ellipse([185, 350, 415, 375], fill=(230, 212, 190))

    # Massa assada
    cor_massa = (95, 55, 30) if tipo_detalhe in ("brigadeiro", "oreo") else (205, 155, 95)
    draw.ellipse([180, 310, 420, 370], fill=cor_massa)

    # Cobertura em espiral com elipses sobrepostas
    r, g, b = cor_cobertura
    cor_c1 = (max(0, r - 15), max(0, g - 15), max(0, b - 15))
    draw.ellipse([175, 275, 425, 340], fill=cor_c1)

    cor_c2 = (r, g, b)
    draw.ellipse([195, 230, 405, 300], fill=cor_c2)

    cor_c3 = (min(255, r + 15), min(255, g + 15), min(255, b + 15))
    draw.ellipse([220, 185, 380, 255], fill=cor_c3)

    cor_c4 = (min(255, r + 25), min(255, g + 25), min(255, b + 25))
    draw.ellipse([250, 145, 350, 215], fill=cor_c4)

    # Detalhe superior
    if tipo_detalhe == "cereja":
        draw.arc([290, 85, 340, 150], start=190, end=340, fill=(100, 50, 20), width=4)
        draw.ellipse([275, 125, 325, 175], fill=(195, 20, 35))
        draw.ellipse([285, 133, 297, 145], fill=(255, 200, 210))
    elif tipo_detalhe == "limao":
        draw.ellipse([275, 120, 325, 170], fill=(245, 210, 40))
        draw.ellipse([282, 127, 318, 163], fill=(255, 240, 120))
        draw.line([(300, 127), (300, 163)], fill=(245, 210, 40), width=2)
        draw.line([(282, 145), (318, 145)], fill=(245, 210, 40), width=2)
        draw.polygon([(320, 120), (345, 110), (335, 130)], fill=(80, 160, 60))
    elif tipo_detalhe == "oreo":
        draw.ellipse([270, 120, 330, 180], fill=(40, 35, 35))
        draw.ellipse([275, 143, 325, 157], fill=(245, 245, 245))
        draw.ellipse([273, 123, 327, 177], outline=(60, 55, 55), width=2)
    elif tipo_detalhe == "brigadeiro":
        granulados = [
            (210, 290, 226, 296), (250, 270, 268, 275), (290, 285, 306, 291),
            (340, 280, 358, 287), (380, 295, 396, 301), (235, 245, 252, 251),
            (280, 235, 298, 240), (325, 240, 342, 246), (360, 250, 376, 257),
            (255, 195, 272, 202), (295, 190, 312, 196), (330, 200, 346, 207),
            (285, 155, 302, 162),
        ]
        for x1, y1, x2, y2 in granulados:
            draw.rounded_rectangle([x1, y1, x2, y2], radius=3, fill=(45, 20, 10))
    elif tipo_detalhe == "frutas":
        draw.ellipse([282, 125, 318, 165], fill=(140, 20, 50))
        for px, py in [(290, 135), (305, 133), (295, 147), (308, 148), (300, 157)]:
            draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(180, 40, 75))
        draw.polygon([(297, 122), (305, 115), (302, 125)], fill=(60, 140, 40))
    else:
        cores_confeitos = [(240, 100, 130), (100, 200, 240), (250, 220, 80), (150, 220, 120), (200, 130, 240)]
        posicoes = [
            (215, 285), (255, 275), (295, 280), (345, 270), (385, 290),
            (240, 240), (285, 230), (330, 235), (365, 245),
            (260, 190), (300, 185), (335, 195),
            (290, 150), (310, 160),
        ]
        for idx, (cx, cy) in enumerate(posicoes):
            draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=cores_confeitos[idx % len(cores_confeitos)])

    return img


class Command(BaseCommand):
    help = "Popula o banco de dados com categorias, produtos, imagens, tabela de frete, cupom, usuarios e pedidos de teste."

    def add_arguments(self, parser):
        parser.add_argument(
            "--senha-admin",
            default=None,
            help="senha do administrador (padrao: variavel ADMIN_PASSWORD; sem ela, gera uma senha aleatoria e mostra no final)",
        )

    def handle(self, *args, **opcoes):
        senha_admin = opcoes.get("senha_admin") or os.getenv("ADMIN_PASSWORD")
        senha_gerada = not senha_admin
        if senha_gerada:
            senha_admin = secrets.token_urlsafe(12)
        admin_criado = False
        self.stdout.write("Iniciando carga de dados...")

        # 1. Categorias
        cat_classicos, _ = Categoria.objects.get_or_create(slug="classicos", defaults={"nome": "Clássicos", "ativa": True})
        cat_veganos, _ = Categoria.objects.get_or_create(slug="veganos", defaults={"nome": "Veganos", "ativa": True})
        cat_tematicos, _ = Categoria.objects.get_or_create(slug="tematicos", defaults={"nome": "Temáticos", "ativa": True})

        # 2. Produtos do catálogo
        catalogo_dados = [
            {
                "slug": "red-velvet",
                "nome": "Cupcake Red Velvet",
                "categoria": cat_classicos,
                "descricao": "Massa aveludada de cacau suave com recheio e cobertura cremosa de cream cheese.",
                "ingredientes": "Farinha de trigo, açúcar, cacau em pó, cream cheese, manteiga, ovos frescos, extrato natural de baunilha, corante vegetal de beterraba.",
                "alergenicos": "Contém glúten, leite e ovos.",
                "preco": Decimal("14.90"),
                "estoque": 25,
                "total_vendas": 140,
                "cor": (200, 35, 50),
                "detalhe": "cereja",
            },
            {
                "slug": "brigadeiro",
                "nome": "Cupcake de Brigadeiro",
                "categoria": cat_classicos,
                "descricao": "Massa macia de chocolate com recheio artesanal de brigadeiro tradicional e granulados nobres.",
                "ingredientes": "Farinha de trigo, chocolate em pó 50%, leite condensado, manteiga, ovos, granulado nobre de chocolate.",
                "alergenicos": "Contém glúten, leite e ovos.",
                "preco": Decimal("12.90"),
                "estoque": 30,
                "total_vendas": 180,
                "cor": (75, 40, 25),
                "detalhe": "brigadeiro",
            },
            {
                "slug": "limao-siciliano",
                "nome": "Cupcake de Limão Siciliano",
                "categoria": cat_classicos,
                "descricao": "Massa fofa aromatizada com raspas de limão siciliano e cobertura leve de merengue tostado.",
                "ingredientes": "Farinha de trigo, açúcar refinado, manteiga, ovos, suco e raspas de limão siciliano fresco.",
                "alergenicos": "Contém glúten, leite e ovos.",
                "preco": Decimal("15.90"),
                "estoque": 18,
                "total_vendas": 110,
                "cor": (250, 230, 110),
                "detalhe": "limao",
            },
            {
                "slug": "baunilha-tradicional",
                "nome": "Cupcake de Baunilha Tradicional",
                "categoria": cat_classicos,
                "descricao": "Massa amanteigada clássica perfumada com fava de baunilha e cobertura delicada de buttercream.",
                "ingredientes": "Farinha de trigo, açúcar refinado, manteiga fresca, ovos, leite integral, favas de baunilha.",
                "alergenicos": "Contém glúten, leite e ovos.",
                "preco": Decimal("9.90"),
                "estoque": 35,
                "total_vendas": 95,
                "cor": (255, 245, 220),
                "detalhe": "confeitos",
            },
            {
                "slug": "cenoura-com-chocolate",
                "nome": "Cupcake de Cenoura com Chocolate",
                "categoria": cat_classicos,
                "descricao": "A clássica combinação de bolo de cenoura fresca com generosa calda de chocolate cremoso.",
                "ingredientes": "Cenouras frescas, farinha de trigo, ovos, óleo vegetal, açúcar, chocolate em pó, leite integral.",
                "alergenicos": "Contém glúten, leite e ovos.",
                "preco": Decimal("10.50"),
                "estoque": 22,
                "total_vendas": 130,
                "cor": (85, 45, 25),
                "detalhe": "brigadeiro",
            },
            {
                "slug": "frutas-vermelhas-vegano",
                "nome": "Cupcake Vegano de Frutas Vermelhas",
                "categoria": cat_veganos,
                "descricao": "Massa fofinha à base de bebida vegetal com recheio artesanal de amoras, morangos e mirtilos.",
                "ingredientes": "Farinha de trigo, açúcar demerara, bebida de amêndoas, óleo de girassol, frutas vermelhas frescas, fermento químico.",
                "alergenicos": "Contém glúten e amêndoas. Não contém ingredientes de origem animal.",
                "preco": Decimal("13.90"),
                "estoque": 15,
                "total_vendas": 70,
                "cor": (185, 45, 85),
                "detalhe": "frutas",
            },
            {
                "slug": "maracuja-vegano",
                "nome": "Cupcake Vegano de Maracujá",
                "categoria": cat_veganos,
                "descricao": "Massa leve preparada com polpa natural de maracujá e cobertura aveludada 100% vegetal.",
                "ingredientes": "Farinha de trigo, polpa natural de maracujá, bebida de aveia, açúcar orgânico, óleo de coco, fermento químico.",
                "alergenicos": "Contém glúten e aveia. Não contém ingredientes de origem animal.",
                "preco": Decimal("12.50"),
                "estoque": 16,
                "total_vendas": 60,
                "cor": (245, 195, 60),
                "detalhe": "confeitos",
            },
            {
                "slug": "banana-com-canela-vegano",
                "nome": "Cupcake Vegano de Banana com Canela",
                "categoria": cat_veganos,
                "descricao": "Massa aromática preparada com bananas maduras, nozes selecionadas e toque especial de canela.",
                "ingredientes": "Bananas maduras, farinha de trigo integral, açúcar mascavo, bebida de soja, nozes picadas, canela em pó, fermento químico.",
                "alergenicos": "Contém glúten, soja e nozes. Não contém ingredientes de origem animal.",
                "preco": Decimal("11.90"),
                "estoque": 20,
                "total_vendas": 85,
                "cor": (210, 160, 115),
                "detalhe": "confeitos",
            },
            {
                "slug": "oreo",
                "nome": "Cupcake de Oreo",
                "categoria": cat_tematicos,
                "descricao": "Massa escura de cacau com pedacinhos de biscoito recheado e cobertura cremosa com crocante de Oreo.",
                "ingredientes": "Farinha de trigo, biscoito de cacau recheado de baunilha, manteiga, ovos, açúcar refinado, leite integral.",
                "alergenicos": "Contém glúten, leite, ovos e derivados de soja.",
                "preco": Decimal("16.90"),
                "estoque": 28,
                "total_vendas": 160,
                "cor": (238, 238, 238),
                "detalhe": "oreo",
            },
            {
                "slug": "unicornio-magico",
                "nome": "Cupcake Unicórnio Mágico",
                "categoria": cat_tematicos,
                "descricao": "Massa colorida sabor algodão doce com espiral em tons pastéis e confeitos brilhantes.",
                "ingredientes": "Farinha de trigo, manteiga, açúcar, leite integral, ovos, confeitos coloridos de açúcar, aroma natural.",
                "alergenicos": "Contém glúten, leite e ovos.",
                "preco": Decimal("15.50"),
                "estoque": 14,
                "total_vendas": 75,
                "cor": (235, 140, 205),
                "detalhe": "confeitos",
            },
            {
                "slug": "cafe-mocha",
                "nome": "Cupcake de Café Mocha",
                "categoria": cat_tematicos,
                "descricao": "Massa enriquecida com café espresso artesanal e cobertura de chocolate meio amargo aromatizado.",
                "ingredientes": "Farinha de trigo, café espresso concentrado, chocolate 50%, manteiga, ovos, açúcar refinado.",
                "alergenicos": "Contém glúten, leite e ovos.",
                "preco": Decimal("13.50"),
                "estoque": 18,
                "total_vendas": 90,
                "cor": (115, 75, 45),
                "detalhe": "brigadeiro",
            },
            {
                "slug": "pistache-nobre",
                "nome": "Cupcake de Pistache Nobre",
                "categoria": cat_tematicos,
                "descricao": "Massa aveludada com pasta pura de pistache e cobertura suave salpicada com pistache picado.",
                "ingredientes": "Farinha de trigo, pasta pura de pistache, açúcar, ovos, manteiga, leite integral, pedaços de pistache.",
                "alergenicos": "Contém glúten, leite, ovos e pistache.",
                "preco": Decimal("16.00"),
                "estoque": 12,
                "total_vendas": 105,
                "cor": (165, 200, 145),
                "detalhe": "confeitos",
            },
        ]

        for item in catalogo_dados:
            produto, _ = Produto.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "categoria": item["categoria"],
                    "nome": item["nome"],
                    "descricao": item["descricao"],
                    "ingredientes": item["ingredientes"],
                    "alergenicos": item["alergenicos"],
                    "preco": item["preco"],
                    "estoque": item["estoque"],
                    "total_vendas": item["total_vendas"],
                    "ativo": True,
                },
            )

            # Só gera a imagem se o produto ainda não tiver uma no disco
            imagem_existe = False
            if produto.imagem:
                try:
                    imagem_existe = produto.imagem.storage.exists(produto.imagem.name)
                except Exception:
                    imagem_existe = False

            if not imagem_existe:
                img = desenhar_cupcake(item["slug"], item["cor"], item["detalhe"])
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                produto.imagem.save(f"{item['slug']}.png", ContentFile(buffer.getvalue()), save=True)

        # 3. Tabela de frete
        carregar_tabela_frete()

        # 4. Cupom de desconto
        cupom, _ = Cupom.objects.update_or_create(
            codigo="CUPCAKE10",
            defaults={
                "tipo": "PERCENTUAL",
                "valor": Decimal("10.00"),
                "valor_minimo_pedido": Decimal("30.00"),
                "data_validade": timezone.now() + timedelta(days=365),
                "ativo": True,
            },
        )

        # 5. Usuário administrador
        admin = Usuario.objects.filter(email="admin@cupcakesgourmet.com").first()
        if not admin:
            admin = Usuario.objects.create_superuser(
                email="admin@cupcakesgourmet.com",
                password=senha_admin,
                nome_completo="Administrador",
            )
            admin_criado = True
        else:
            admin.is_staff = True
            admin.is_superuser = True
            admin.email_confirmado = True
            admin.save()

        # 6. Usuário cliente com endereço em Medianeira/PR
        cliente = Usuario.objects.filter(email="cliente@teste.com").first()
        if not cliente:
            cliente = Usuario.objects.create_user(
                email="cliente@teste.com",
                password="Cliente@123456",
                nome_completo="Cliente Teste",
                email_confirmado=True,
            )
        else:
            cliente.email_confirmado = True
            cliente.save()

        endereco, _ = Endereco.objects.update_or_create(
            usuario=cliente,
            cep="85884-000",
            defaults={
                "logradouro": "Rua das Flores",
                "numero": "123",
                "complemento": "",
                "bairro": "Centro",
                "cidade": "Medianeira",
                "uf": "PR",
                "principal": True,
            },
        )

        # 7. Pedidos de demonstração para o cliente
        end_str = f"{endereco.logradouro}, {endereco.numero}\n{endereco.bairro} — {endereco.cidade}/{endereco.uf}\nCEP {endereco.cep}"

        # Pedido 1: AGUARDANDO_PAGAMENTO por PIX
        p1 = Pedido.objects.filter(numero="CG-DEMO-001").first()
        if not p1:
            p1 = Pedido.objects.create(
                numero="CG-DEMO-001",
                usuario=cliente,
                endereco_entrega=end_str,
                subtotal=Decimal("29.80"),
                valor_desconto=Decimal("0.00"),
                cupom=None,
                valor_frete=Decimal("8.00"),
                valor_total=Decimal("37.80"),
                forma_pagamento="PIX",
                status="AGUARDANDO_PAGAMENTO",
                estoque_baixado=False,
                pix_expira_em=timezone.now() + timedelta(minutes=30),
                detalhes_pagamento={
                    "codigo": "00020126580014br.gov.bcb.pix0136123e4567-e89b-12d3-a456-426614174000520400005303986540537.805802BR5916CUPCAKES GOURMET6010MEDIANEIRA62070503***6304ABCD"
                },
            )
            prod_rv = Produto.objects.get(slug="red-velvet")
            ItemPedido.objects.create(
                pedido=p1,
                produto=prod_rv,
                nome_produto=prod_rv.nome,
                preco_unitario=prod_rv.preco,
                quantidade=2,
                subtotal=Decimal("29.80"),
            )
            HistoricoStatus.objects.create(pedido=p1, status="AGUARDANDO_PAGAMENTO")
            ReservaEstoque.objects.update_or_create(
                usuario=cliente,
                produto=prod_rv,
                defaults={"quantidade": 2, "expira_em": p1.pix_expira_em, "ativa": True},
            )
            Notificacao.objects.create(
                usuario=cliente,
                pedido=p1,
                titulo="Aguardando pagamento",
                mensagem=f"Pedido {p1.numero}: Aguardando pagamento.",
            )

        # Pedido 2: EM_PREPARACAO
        p2 = Pedido.objects.filter(numero="CG-DEMO-002").first()
        if not p2:
            prod_limao = Produto.objects.get(slug="limao-siciliano")
            p2 = Pedido.objects.create(
                numero="CG-DEMO-002",
                usuario=cliente,
                endereco_entrega=end_str,
                subtotal=Decimal("31.80"),
                valor_desconto=Decimal("3.18"),
                cupom=cupom,
                valor_frete=Decimal("8.00"),
                valor_total=Decimal("36.62"),
                forma_pagamento="CARTAO",
                status="EM_PREPARACAO",
                estoque_baixado=True,
                pix_expira_em=None,
                detalhes_pagamento={
                    "ultimos_digitos": "1111",
                    "bandeira": "Visa",
                    "parcelas": 1,
                    "valor_parcela": "36.62",
                },
            )
            ItemPedido.objects.create(
                pedido=p2,
                produto=prod_limao,
                nome_produto=prod_limao.nome,
                preco_unitario=prod_limao.preco,
                quantidade=2,
                subtotal=Decimal("31.80"),
            )
            CupomUso.objects.get_or_create(cupom=cupom, usuario=cliente)
            HistoricoStatus.objects.create(pedido=p2, status="PAGAMENTO_CONFIRMADO")
            HistoricoStatus.objects.create(pedido=p2, status="EM_PREPARACAO")
            Notificacao.objects.create(
                usuario=cliente,
                pedido=p2,
                titulo="Pagamento confirmado",
                mensagem=f"Pedido {p2.numero}: Pagamento confirmado.",
            )
            Notificacao.objects.create(
                usuario=cliente,
                pedido=p2,
                titulo="Em preparação",
                mensagem=f"Pedido {p2.numero}: Em preparação.",
            )

        # Pedido 3: ENTREGUE
        p3 = Pedido.objects.filter(numero="CG-DEMO-003").first()
        if not p3:
            prod_oreo = Produto.objects.get(slug="oreo")
            p3 = Pedido.objects.create(
                numero="CG-DEMO-003",
                usuario=cliente,
                endereco_entrega=end_str,
                subtotal=Decimal("33.80"),
                valor_desconto=Decimal("0.00"),
                cupom=None,
                valor_frete=Decimal("8.00"),
                valor_total=Decimal("41.80"),
                forma_pagamento="CARTAO",
                status="ENTREGUE",
                estoque_baixado=True,
                pix_expira_em=None,
                detalhes_pagamento={
                    "ultimos_digitos": "1111",
                    "bandeira": "Visa",
                    "parcelas": 1,
                    "valor_parcela": "41.80",
                },
            )
            ItemPedido.objects.create(
                pedido=p3,
                produto=prod_oreo,
                nome_produto=prod_oreo.nome,
                preco_unitario=prod_oreo.preco,
                quantidade=2,
                subtotal=Decimal("33.80"),
            )
            HistoricoStatus.objects.create(pedido=p3, status="PAGAMENTO_CONFIRMADO")
            HistoricoStatus.objects.create(pedido=p3, status="EM_PREPARACAO")
            HistoricoStatus.objects.create(pedido=p3, status="SAIU_PARA_ENTREGA")
            HistoricoStatus.objects.create(pedido=p3, status="ENTREGUE")
            Notificacao.objects.create(
                usuario=cliente,
                pedido=p3,
                titulo="Pagamento confirmado",
                mensagem=f"Pedido {p3.numero}: Pagamento confirmado.",
            )
            Notificacao.objects.create(
                usuario=cliente,
                pedido=p3,
                titulo="Em preparação",
                mensagem=f"Pedido {p3.numero}: Em preparação.",
            )
            Notificacao.objects.create(
                usuario=cliente,
                pedido=p3,
                titulo="Saiu para entrega",
                mensagem=f"Pedido {p3.numero}: Saiu para entrega.",
            )
            Notificacao.objects.create(
                usuario=cliente,
                pedido=p3,
                titulo="Entregue",
                mensagem=f"Pedido {p3.numero}: Entregue.",
            )

        self.stdout.write(self.style.SUCCESS("Dados carregados com sucesso!"))
        self.stdout.write("--- Resumo da carga ---")
        self.stdout.write(f"- Categorias: {Categoria.objects.count()} ativas (Clássicos, Veganos, Temáticos)")
        self.stdout.write(f"- Produtos: {Produto.objects.count()} cupcakes com ilustrações PNG 600x600")
        self.stdout.write("- Frete: Tabela por UF carregada (PR, SC, RS, SP, RJ, MG)")
        self.stdout.write("- Cupom ativo: CUPCAKE10 (10% de desconto)")
        if not admin_criado:
            self.stdout.write("- Administrador: admin@cupcakesgourmet.com já existia, a senha não foi alterada")
        elif senha_gerada:
            self.stdout.write(f"- Administrador: admin@cupcakesgourmet.com / senha gerada: {senha_admin} (anote agora, ela não aparece de novo)")
        else:
            self.stdout.write("- Administrador: admin@cupcakesgourmet.com (senha definida por você)")
        self.stdout.write("- Cliente de teste: cliente@teste.com / Cliente@123456 (Medianeira/PR)")
        self.stdout.write("- Pedidos de demonstração: 3 (PIX pendente, Em preparação, Entregue)")
