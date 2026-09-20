from django.urls import path

from painel import views

app_name = "painel"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("produtos/", views.produtos_lista, name="produtos_lista"),
    path("produtos/novo/", views.produto_criar, name="produto_criar"),
    path("produtos/<int:pk>/editar/", views.produto_editar, name="produto_editar"),
    path("produtos/<int:pk>/desativar/", views.produto_desativar, name="produto_desativar"),
    path("produtos/<int:pk>/reativar/", views.produto_reativar, name="produto_reativar"),
    path("categorias/", views.categorias_lista, name="categorias_lista"),
    path("categorias/nova/", views.categoria_criar, name="categoria_criar"),
    path("categorias/<int:pk>/editar/", views.categoria_editar, name="categoria_editar"),
    path("categorias/<int:pk>/desativar/", views.categoria_desativar, name="categoria_desativar"),
    path("categorias/<int:pk>/reativar/", views.categoria_reativar, name="categoria_reativar"),
    path("pedidos/", views.pedidos_lista, name="pedidos_lista"),
    path("pedidos/<str:numero>/", views.pedido_detalhe, name="pedido_detalhe"),
    path("pedidos/<str:numero>/avancar/", views.pedido_avancar_status, name="pedido_avancar_status"),
    path("pedidos/<str:numero>/cancelar/", views.pedido_cancelar, name="pedido_cancelar"),
]
