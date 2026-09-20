from django.urls import path

from pedidos import views

app_name = "pedidos"

urlpatterns = [
    path("", views.historico, name="historico"),
    path("notificacoes/", views.notificacoes, name="notificacoes"),
    path("notificacoes/<int:pk>/lida/", views.marcar_notificacao_lida, name="marcar_notificacao_lida"),
    path("notificacoes/lidas/", views.marcar_todas_lidas, name="marcar_todas_lidas"),
    path("pedido/<str:numero>/", views.pedido_detalhe, name="pedido_detalhe"),
    path("pedido/<str:numero>/confirmar-pix/", views.confirmar_pix, name="confirmar_pix"),
    path("pedido/<str:numero>/repetir/", views.repetir_pedido, name="repetir_pedido"),
    path("checkout/", views.checkout_endereco, name="checkout_endereco"),
    path("checkout/pagamento/", views.checkout_pagamento, name="checkout_pagamento"),
    path("checkout/resumo/", views.checkout_resumo, name="checkout_resumo"),
    path("checkout/confirmar/", views.checkout_confirmar, name="checkout_confirmar"),
    path("cep/consultar/", views.consultar_cep, name="consultar_cep"),
    path("cupom/aplicar/", views.aplicar_cupom, name="aplicar_cupom"),
    path("cupom/remover/", views.remover_cupom, name="remover_cupom"),
    path("resumo/", views.obter_resumo, name="resumo"),
]
