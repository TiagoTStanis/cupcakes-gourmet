from decimal import Decimal

from django.conf import settings
from django.db import models


class TabelaFreteUF(models.Model):
    uf = models.CharField("UF", max_length=2, unique=True)
    valor = models.DecimalField("valor", max_digits=6, decimal_places=2)
    prazo_dias = models.PositiveIntegerField("prazo em dias")

    class Meta:
        verbose_name = "tabela de frete por UF"
        verbose_name_plural = "tabelas de frete por UF"
        ordering = ["uf"]

    def __str__(self):
        return f"{self.uf}: R$ {self.valor} ({self.prazo_dias} dias)"


class Cupom(models.Model):
    TIPO_CHOICES = [
        ("PERCENTUAL", "Percentual"),
        ("FIXO", "Fixo"),
    ]

    codigo = models.CharField("código", max_length=30, unique=True)
    tipo = models.CharField("tipo", max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField("valor", max_digits=6, decimal_places=2)
    valor_minimo_pedido = models.DecimalField(
        "valor mínimo do pedido",
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    data_validade = models.DateTimeField("data de validade")
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "cupom"
        verbose_name_plural = "cupons"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} ({self.tipo} {self.valor})"


class CupomUso(models.Model):
    cupom = models.ForeignKey(
        Cupom,
        on_delete=models.CASCADE,
        related_name="usos",
        verbose_name="cupom",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cupons_usados",
        verbose_name="usuário",
    )
    data_uso = models.DateTimeField("data de uso", auto_now_add=True)

    class Meta:
        verbose_name = "uso de cupom"
        verbose_name_plural = "usos de cupons"
        unique_together = ("cupom", "usuario")
        ordering = ["-data_uso"]

    def __str__(self):
        return f"{self.usuario} usou {self.cupom.codigo}"


class ReservaEstoque(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    produto = models.ForeignKey("catalogo.Produto", on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField()
    criada_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField(db_index=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "produto"], name="reserva_usuario_produto_unica"),
            models.CheckConstraint(condition=models.Q(quantidade__gt=0), name="reserva_quantidade_positiva"),
        ]


class Pedido(models.Model):
    FORMA_PAGAMENTO_CHOICES = [("CARTAO", "Cartão"), ("PIX", "PIX")]
    STATUS_CHOICES = [
        ("AGUARDANDO_PAGAMENTO", "Aguardando pagamento"),
        ("PAGAMENTO_CONFIRMADO", "Pagamento confirmado"),
        ("EM_PREPARACAO", "Em preparação"),
        ("SAIU_PARA_ENTREGA", "Saiu para entrega"),
        ("ENTREGUE", "Entregue"),
        ("CANCELADO", "Cancelado"),
    ]

    numero = models.CharField(max_length=20, unique=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos")
    endereco_entrega = models.TextField()
    subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    valor_desconto = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    cupom = models.ForeignKey(Cupom, on_delete=models.SET_NULL, null=True, blank=True)
    valor_frete = models.DecimalField(max_digits=6, decimal_places=2)
    valor_total = models.DecimalField(max_digits=8, decimal_places=2)
    forma_pagamento = models.CharField(max_length=6, choices=FORMA_PAGAMENTO_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AGUARDANDO_PAGAMENTO")
    estoque_baixado = models.BooleanField(default=False)
    pix_expira_em = models.DateTimeField(null=True, blank=True)
    detalhes_pagamento = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.numero


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("catalogo.Produto", on_delete=models.PROTECT)
    nome_produto = models.CharField(max_length=150)
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    quantidade = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantidade__gt=0), name="item_pedido_quantidade_positiva"),
        ]


class HistoricoStatus(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="historico_status")
    status = models.CharField(max_length=20, choices=Pedido.STATUS_CHOICES)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "pk"]


class Notificacao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificacoes")
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=True, blank=True)
    titulo = models.CharField(max_length=100)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em", "-pk"]

    def __str__(self):
        return self.titulo
