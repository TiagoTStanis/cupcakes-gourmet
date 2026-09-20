from decimal import Decimal

from django.conf import settings
from django.db import models

from catalogo.models import Produto


class Carrinho(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carrinho",
        verbose_name="usuário",
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "carrinho"
        verbose_name_plural = "carrinhos"

    def __str__(self):
        return f"Carrinho de {self.usuario}"

    @property
    def total_itens(self):
        return sum(item.quantidade for item in self.itens.all())

    @property
    def total_geral(self):
        total = Decimal("0.00")
        for item in self.itens.select_related("produto"):
            total += item.subtotal
        return total


class ItemCarrinho(models.Model):
    carrinho = models.ForeignKey(
        Carrinho,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="carrinho",
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="itens_carrinho",
        verbose_name="produto",
    )
    quantidade = models.PositiveIntegerField("quantidade", default=1)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "item do carrinho"
        verbose_name_plural = "itens do carrinho"
        unique_together = ("carrinho", "produto")
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"

    @property
    def subtotal(self):
        return Decimal(str(self.produto.preco)) * self.quantidade
