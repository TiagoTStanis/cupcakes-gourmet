from django.urls import path

from carrinho import views

app_name = "carrinho"

urlpatterns = [
    path("", views.carrinho_detalhe, name="detalhe"),
    path("adicionar/", views.adicionar_item, name="adicionar"),
    path("alterar/", views.alterar_quantidade_item, name="alterar"),
    path("remover/", views.remover_item, name="remover"),
    path("remover/<int:produto_id>/", views.remover_item, name="remover_por_id"),
]
